import os
import json
import time
import csv
import re
from typing import List, Dict
from openai import OpenAI
from scrapling import Fetcher
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. CONFIGURATION
# ==========================================
LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1" 
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
PROXY_TOKEN = "sk-pro-rahul"

client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)

# ==========================================
# 2. TARGET & STATE MANAGEMENT (7-Day Cycle)
# ==========================================
STATE_FILE = "data/scraper_state.json"
TARGETS_FILE = "data/targets.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "new_cursor": 0,    # Where we are in scanning entirely new endpoints
        "rescan_cursor": 0, # Where we are in rescanning older endpoints (Starts day 8)
        "day_count": 1
    }

def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_targets() -> List[str]:
    if os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE, 'r') as f:
            return json.load(f)
    return []

# ==========================================
# 3. PARALLEL STEALTH SOURCING
# ==========================================
def scrape_single_target(url: str, fetcher: Fetcher) -> List[Dict]:
    raw_leads = []
    pos_keywords = [r'\bpm\b', r'\bproduct manager\b', r'\bfounding pm\b', r'\bproduct owner\b']
    neg_keywords = [r'\bsales\b', r'\bdevelopment representative\b', r'\bsdr\b', r'\bbdr\b', r'\bengineer\b', r'\bmarketing\b']
    
    try:
        is_ashby = 'ashbyhq' in url
        slug = url.split('/')[-1] if is_ashby else url.split('/')[-2]
        
        response = fetcher.get(url)
        if response.status == 200:
            data = response.json()
            jobs = data.get('jobs', [])
            company_name = slug.capitalize()
            
            for job in jobs:
                title = job.get('title', '').lower()
                is_pm = any(re.search(kw, title) for kw in pos_keywords)
                is_noise = any(re.search(kw, title) for kw in neg_keywords)
                
                if is_pm and not is_noise:
                    job_url = job.get('jobUrl') if is_ashby else job.get('absolute_url')
                    desc = job.get('descriptionPlain', '')[:1500] if is_ashby else "Greenhouse JD - Filtered by Title"
                    raw_leads.append({
                        'company': company_name,
                        'role': job.get('title'),
                        'url': job_url,
                        'description': desc
                    })
    except:
        pass
    return raw_leads

def run_sourcing_cycle(chunk_size=500):
    all_targets = load_targets()
    total_targets = len(all_targets)
    if total_targets == 0:
        print("❌ No targets found. Run build_target_db.py first.")
        return []
        
    state = load_state()
    fetcher = Fetcher()
    all_leads = []
    
    print(f"🗓️  Day {state['day_count']} of Sourcing Cycle.")
    
    # --- PHASE 1: Fetch NEW endpoints (chunk_size) ---
    start_new = state['new_cursor']
    end_new = min(start_new + chunk_size, total_targets)
    
    if start_new >= total_targets:
        print("🔄 Reached end of targets! Resetting new_cursor.")
        start_new = 0
        end_new = chunk_size
        
    new_targets = all_targets[start_new:end_new]
    print(f"🚀 Scanning {len(new_targets)} NEW endpoints (Index {start_new} to {end_new})...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        for batch in executor.map(lambda url: scrape_single_target(url, fetcher), new_targets):
            all_leads.extend(batch)
            
    state['new_cursor'] = end_new
    
    # --- PHASE 2: Fetch RESCAN endpoints (Starts after Day 7) ---
    if state['day_count'] > 7:
        start_rescan = state['rescan_cursor']
        end_rescan = min(start_rescan + chunk_size, total_targets)
        
        if start_rescan >= total_targets:
            start_rescan = 0
            end_rescan = chunk_size
            
        rescan_targets = all_targets[start_rescan:end_rescan]
        print(f"🔄 Rescanning {len(rescan_targets)} OLD endpoints (7-Day Refresh: Index {start_rescan} to {end_rescan})...")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            for batch in executor.map(lambda url: scrape_single_target(url, fetcher), rescan_targets):
                all_leads.extend(batch)
                
        state['rescan_cursor'] = end_rescan
        
    state['day_count'] += 1
    save_state(state)
    return all_leads

# ==========================================
# 4. FILTERING (AI Signal with Quota)
# ==========================================
def filter_and_tailor(leads: List[Dict], quota: int) -> List[List]:
    if not leads: return []
    print(f"🧠 Evaluation Phase: Target = {quota} Gold Leads.")
    approved_rows = []
    
    for lead in leads:
        if len(approved_rows) >= quota:
            print(f"🛑 Daily Quota Reached ({quota}/{quota}).")
            break
            
        prompt = f"Role: {lead['role']}\nCompany: {lead['company']}\nJD: {lead['description']}\n\nSTRICT: If NOT PM, Score=1. If High Fit 0-to-1 PM, Score > 7.\nOutput JSON: {{\"score\": int, \"summary\": \"str\", \"cluster\": \"str\"}}"
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=15
            )
            eval_data = json.loads(response.choices[0].message.content.replace("```json", "").replace("```", ""))
            score = eval_data.get('score', 0)
            if score > 7:
                print(f"🔥 MATCH ({score}/10) [{len(approved_rows)+1}/{quota}]: {lead['company']} - {lead['role']}")
                approved_rows.append([time.strftime("%Y-%m-%d"), lead['company'], lead['role'], f"{score}/10", "Pending", lead['url'], f"cv-{eval_data.get('cluster', 'core').lower().replace(' ', '-')}.pdf"])
        except:
            pass
            
    return approved_rows

def save_to_csv(rows: List[List]):
    if not rows: return
    filename = f"industrial_leads_{time.strftime('%Y%m%d')}.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Company', 'Role', 'Score', 'Status', 'URL', 'CV_Type'])
        writer.writerows(rows)
    print(f"✅ CSV created: {filename}")

if __name__ == "__main__":
    print("=== 🏗️  INDUSTRIAL ENGINE V5 (7-DAY HYBRID PACING) INITIATED ===")
    start_time = time.time()
    
    raw_leads = run_sourcing_cycle(chunk_size=500) 
    tailored_rows = filter_and_tailor(raw_leads, quota=50)
    save_to_csv(tailored_rows)
    
    end_time = time.time()
    print(f"=== 🏁 PROCESS COMPLETE IN {int(end_time - start_time)}s ===")
