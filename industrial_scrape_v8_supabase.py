import os
import json
import time
import csv
import re
import urllib.parse
from typing import List, Dict
from openai import OpenAI
from scrapling import Fetcher
from concurrent.futures import ThreadPoolExecutor
from supabase import create_client, Client

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

# ==========================================
# 2. SUPABASE OPERATIONS
# ==========================================
def is_url_in_db(url: str) -> bool:
    try:
        response = supabase.table("leads").select("id").eq("url", url).execute()
        return len(response.data) > 0
    except:
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
def scrape_single_target(url: str, fetcher: Fetcher) -> List[Dict]:
    raw_leads = []
    pos_keywords = [r'\bpm\b', r'\bproduct manager\b', r'\bproduct owner\b', r'\bapm\b', r'\bassociate product manager\b', r'\bjunior product manager\b']
    neg_keywords = [r'\bsales\b', r'\bdevelopment representative\b', r'\bsdr\b', r'\bbdr\b', r'\bengineer\b', r'\bmarketing\b', r'\bsenior\b', r'\bstaff\b', r'\bprincipal\b', r'\blead\b', r'\bvp\b', r'\bhead\b', r'\bdirector\b']
    
    try:
        is_ashby = 'ashbyhq' in url
        slug = url.split('/')[-1] if is_ashby else url.split('/')[-2]
        response = fetcher.get(url)
        
        if response.status == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            company_name = slug.capitalize()
            
            for job in jobs:
                job_url = job.get('jobUrl') if is_ashby else job.get('absolute_url')
                
                # 🔥 DB DEDUP: Skip if already in Supabase
                if is_url_in_db(job_url):
                    continue

                title = job.get('title', '').lower()
                if any(re.search(kw, title) for kw in pos_keywords) and not any(re.search(kw, title) for kw in neg_keywords):
                    desc = ""
                    if is_ashby:
                        desc = job.get('descriptionPlain', '')[:1500]
                    else:
                        try:
                            detail_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job.get('id')}"
                            detail_resp = fetcher.get(detail_url)
                            if detail_resp.status == 200:
                                desc = detail_resp.json().get('content', '')[:1500]
                        except: pass

                    if not desc or len(desc.strip()) < 100:
                        continue 

                    raw_leads.append({
                        'company': company_name, 'role': job.get('title'),
                        'url': job_url, 'description': desc
                    })
    except: pass
    return raw_leads

def run_pipeline(quota=50, chunk_size=500):
    all_targets = []
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE, 'r') as f: all_targets = json.load(f)
    
    total_targets = len(all_targets)
    state = load_json(STATE_FILE, {"new_cursor": 0, "rescan_cursor": 0, "day_count": 1})
    fetcher = Fetcher()
    
    matches_count = 0
    total_scanned_this_session = 0

    print(f"🚀 Starting Continuous Sourcing Loop (Daily Goal: {quota} Gold Leads)")

    while matches_count < quota and total_scanned_this_session < total_targets:
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
        for lead in raw_leads:
            if matches_count >= quota: break
            
            prompt = f"""
            Role: {lead['role']}
            Company: {lead['company']}
            JD: {lead['description']}
            
            STRICT RULES:
            1. If NOT a PM role, Score=1.
            2. If the JD requires MORE than 2 years of experience (e.g. "3+ years", "5 years"), Score=1.
            3. Target: Entry-level/Junior PM (0-1 years). High Fit > 7.
            
            Output JSON: {{"score": int, "cluster": "str", "dm_draft": "str"}}
            """
            try:
                resp = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.1, timeout=15)
                data = json.loads(resp.choices[0].message.content.replace("```json", "").replace("```", ""))
                score = data.get('score', 0)
                
                if score > 7:
                    print(f"🔥 GOLD LEAD [{matches_count + 1}/{quota}]: {lead['company']} - {lead['role']} ({score}/10)")
                    supabase.table("leads").insert({
                        "company": lead['company'], "role": lead['role'], "score": f"{score}/10",
                        "url": lead['url'], "description": lead['description'],
                        "cluster": data.get('cluster', 'Core'), "dm_draft": data.get('dm_draft', ''),
                        "status": "Pending"
                    }).execute()
                    matches_count += 1
                    update_daily_stats(high_match=1)
            except Exception as e: pass

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
