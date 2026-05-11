import os
import json
import time
import csv
import re
import urllib.parse
from html import unescape
from typing import List, Dict
from openai import OpenAI
from scrapling import Fetcher
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client
from cli.resolve_targets import normalize_api_url, provider_for_url

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Credentials
SUPABASE_URL = "https://pzasaxdmufmhrxdppsbk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB6YXNheGRtdWZtaHJ4ZHBwc2JrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM5NzQ5NywiZXhwIjoyMDkwOTczNDk3fQ.ZqHBzMgj1Ot8yxl2nZfIdgk7PR0bmWWYp2YF8JyWePk"

LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1" 
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
PROXY_TOKEN = "sk-pro-rahul"

# Clients
client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Files
STATE_FILE = "data/scraper_state.json"
TARGETS_FILE = "data/targets.json"
RESOLVED_TARGETS_FILE = "data/resolved_targets.json"

# ==========================================
# 1.5. HELPER FUNCTIONS
# ==========================================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, path)

def strip_html(value: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', unescape(value or ''))).strip()

def load_scan_targets() -> List[Dict]:
    resolved = load_json(RESOLVED_TARGETS_FILE, [])
    if resolved:
        print(f"✅ Loaded {len(resolved)} resolved ATS targets from {RESOLVED_TARGETS_FILE}")
        return [
            {
                "company": item.get("company") or item.get("api_url", "").split("/")[-2].capitalize(),
                "api_url": item["api_url"],
                "provider": item.get("provider") or provider_for_url(item["api_url"]),
                "source": item.get("source", "resolved_targets"),
            }
            for item in resolved
            if item.get("api_url")
        ]

    legacy_targets = load_json(TARGETS_FILE, [])
    print(f"⚠️ No resolved targets found; falling back to {len(legacy_targets)} generated URLs.")
    return [
        {
            "company": "",
            "api_url": normalize_api_url(url),
            "provider": provider_for_url(url),
            "source": "legacy_targets",
        }
        for url in legacy_targets
        if isinstance(url, str)
    ]

# ==========================================
# 2. SUPABASE OPERATIONS
# ==========================================
def is_url_in_db(url: str) -> bool:
    try:
        response = supabase.table("leads").select("id").eq("url", url).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"⚠️ DB dedup check failed for {url}: {e}")
        return False

def update_daily_stats(scraped=0, filtered=0, high_match=0):
    today = time.strftime("%Y-%m-%d")
    try:
        # Check if record exists for today
        res = supabase.table("daily_stats").select("*").eq("date", today).execute()
        if not res.data:
            supabase.table("daily_stats").insert({
                "date": today,
                "scraped_count": scraped,
                "filtered_count": filtered,
                "high_match_count": high_match
            }).execute()
        else:
            current = res.data[0]
            supabase.table("daily_stats").update({
                "scraped_count": current["scraped_count"] + scraped,
                "filtered_count": current["filtered_count"] + filtered,
                "high_match_count": current["high_match_count"] + high_match
            }).eq("date", today).execute()
    except Exception as e:
        print(f"⚠️ Stats Update Failed: {e}")

# ==========================================
# 3. SOURCING LOGIC
# ==========================================
def scrape_single_target(target: Dict, fetcher: Fetcher) -> List[Dict]:
    raw_leads = []
    pos_keywords = [r'\bpm\b', r'\bproduct manager\b', r'\bproduct owner\b', r'\bapm\b', r'\bassociate product manager\b', r'\bjunior product manager\b', r'\bbuilder\b']
    neg_keywords = [r'\bsales\b', r'\bdevelopment representative\b', r'\bsdr\b', r'\bbdr\b']
    
    try:
        url = target["api_url"]
        provider = target.get("provider") or provider_for_url(url)
        board_match = re.search(r'/boards/([^/]+)/jobs', url)
        board_slug = board_match.group(1) if board_match else ""
        response = fetcher.get(url)
        
        if response.status == 404:
            print(f"❌ WRONG SLUG [{provider}]: {url}")
            return raw_leads
        elif response.status != 200:
            print(f"⚠️ API FAILURE [{provider}] {url}: HTTP {response.status}")
            return raw_leads

        data = response.json()
        jobs = data if provider == "lever" and isinstance(data, list) else data.get('jobs', [])
        company_name = target.get("company") or board_slug.capitalize()
        if not jobs:
            print(f"ℹ️ INACTIVE [{company_name or provider}]: {url} (No jobs found)")
            return raw_leads
        print(f"🔎 {company_name or url}: {len(jobs)} jobs from {provider}")
        
        for job in jobs:
            if provider == "ashby":
                job_url = job.get('jobUrl')
                role = job.get('title', '')
                location = str(job.get('location') or '')
                desc = strip_html(job.get('descriptionPlain', '') or job.get('descriptionHtml', ''))[:2000]
            elif provider == "lever":
                categories = job.get('categories') or {}
                job_url = job.get('hostedUrl') or job.get('applyUrl')
                role = job.get('text', '')
                location = categories.get('location', '')
                desc = strip_html(job.get('descriptionPlain', '') or job.get('description', ''))[:2000]
            else:
                job_url = job.get('absolute_url')
                role = job.get('title', '')
                location = (job.get('location') or {}).get('name', '')
                desc = strip_html(job.get('content', ''))[:2000]
                if not desc and board_slug and job.get('id'):
                    try:
                        detail_url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs/{job.get('id')}"
                        detail_resp = fetcher.get(detail_url)
                        if detail_resp.status == 200:
                            desc = strip_html(detail_resp.json().get('content', ''))[:2000]
                    except Exception as e:
                        print(f"⚠️ Detail fetch failed for {job_url}: {e}")
            
            if not job_url or is_url_in_db(job_url):
                continue

            title = role.lower()
            if any(re.search(kw, title) for kw in pos_keywords) and not any(re.search(kw, title) for kw in neg_keywords):
                if not desc or len(desc.strip()) < 100:
                    print(f"⚠️ Skipping {company_name} - {role}: missing/short description")
                    continue

                raw_leads.append({
                    'company': company_name, 'role': role, 'url': job_url,
                    'description': desc, 'location': location, 'provider': provider
                })
    except Exception as e:
        print(f"⚠️ Target scrape failed {target}: {e}")
    return raw_leads

def run_pipeline(quota=50, chunk_size=500, max_scans=500):
    all_targets = load_scan_targets()
    
    total_targets = len(all_targets)
    state = load_json(STATE_FILE, {"new_cursor": 0, "rescan_cursor": 0, "day_count": 1})
    fetcher = Fetcher()
    
    matches_count = 0
    total_scanned_this_session = 0

    print(f"🚀 Starting Global-Local Sourcing (Quota: {quota}, Max Scans: {max_scans})")

    while matches_count < quota and total_scanned_this_session < max_scans:
        # 1. Select Targets for this chunk
        start_new = state['new_cursor']
        end_new = min(start_new + chunk_size, total_targets)
        
        targets_to_scan = all_targets[start_new:end_new]
        if state['day_count'] > 7:
            # Also add rescan chunk
            start_rescan = state['rescan_cursor']
            end_rescan = min(start_rescan + chunk_size, total_targets)
            targets_to_scan += all_targets[start_rescan:end_rescan]
            state['rescan_cursor'] = 0 if end_rescan >= total_targets else end_rescan

        if not targets_to_scan:
            print("🔄 Cycle complete. Resetting cursors.")
            state['new_cursor'] = 0
            state['rescan_cursor'] = 0
            continue

        print(f"🕵️ Scanning batch (Index {start_new} to {end_new})...")
        raw_leads = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            for batch in executor.map(lambda u: scrape_single_target(u, fetcher), targets_to_scan):
                raw_leads.extend(batch)
        
        total_scanned_this_session += len(targets_to_scan)
        update_daily_stats(scraped=len(targets_to_scan), filtered=len(raw_leads))
        
        # 2. Evaluate Batch
        debug_csv = "debug_scanned_leads.csv"
        file_exists = os.path.exists(debug_csv)
        
        with open(debug_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Company', 'Role', 'Score', 'URL', 'Cluster', 'JD_Snippet'])

            for lead in raw_leads:
                if matches_count >= quota: break
                
                prompt = f"""
                    Role: {lead['role']}
                    Company: {lead['company']}
                    Location: {lead.get('location', 'Unknown')}
                    JD: {lead['description']}
                
                STRICT RULES:
                1. If NOT a PM role, Score=1.
                2. If the JD requires MORE than 2 years of experience (e.g. "3+ years", "5 years"), Score=1.
                3. LOCATION (GLOBAL-LOCAL HYBRID): 
                   - Accept if located in India (Bangalore, Hyderabad, Pune, Mumbai, Delhi, etc.)
                   - Accept if explicitly mentions Remote hiring from India/APAC.
                   - Accept if company is Global (US/UK/EU) but JD mentions an India office or India-based team.
                   - Reject if strictly US/UK/EU ONLY with no India path.
                4. Target: Entry-level/Junior PM (0-1 years). High Fit > 7.
                
                Output JSON: {{"score": int, "cluster": "str", "dm_draft": "str"}}
                """
                try:
                    resp = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.1, timeout=15)
                    data = json.loads(resp.choices[0].message.content.replace("```json", "").replace("```", ""))
                    score = data.get('score', 0)
                    
                    # Log EVERYTHING to CSV for manual inspection
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S"),
                        lead['company'], lead['role'], score, lead['url'], 
                        data.get('cluster', 'N/A'), lead['description'][:200].replace('\n', ' ')
                    ])

                    if score >= 4:
                        print(f"📡 POTENTIAL LEAD [{matches_count + 1}/{quota}]: {lead['company']} - {lead['role']} ({score}/10)")
                        supabase.table("leads").insert({
                            "company": lead['company'], "role": lead['role'], "score": f"{score}/10",
                            "url": lead['url'], "description": lead['description'],
                            "cluster": data.get('cluster', 'Core'), "dm_draft": data.get('dm_draft', ''),
                            "status": "Pending"
                        }).execute()
                        matches_count += 1
                        update_daily_stats(high_match=1)
                except Exception as e:
                    print(f"⚠️ Evaluation/insert failed for {lead.get('company')} - {lead.get('role')}: {e}")

        # 3. Advance state for next chunk
        state['new_cursor'] = 0 if end_new >= total_targets else end_new
        save_json(STATE_FILE, state)
        
        if matches_count < quota:
            print(f"⏳ Only {matches_count}/{quota} found. Scanning next chunk...")

    state['day_count'] += 1
    save_json(STATE_FILE, state)
    print(f"✅ Daily Goal Reached! Scanned {total_scanned_this_session} companies to find {matches_count} Gold Leads.")

if __name__ == "__main__":
    print("=== 🏗️ INDUSTRIAL ENGINE V8 (SUPABASE EDITION) ===")
    run_pipeline(quota=50)
    print("=== 🏁 DAILY SYNC COMPLETE ===")
