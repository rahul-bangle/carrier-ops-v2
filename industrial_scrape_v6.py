import os
import json
import time
import csv
import re
from typing import List, Dict
from openai import OpenAI
from scrapling import Fetcher
from concurrent.futures import ThreadPoolExecutor
from composio import ComposioToolSet, Action

# ==========================================
# 1. CONFIGURATION
# ==========================================
LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1" 
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
PROXY_TOKEN = "sk-pro-rahul"
SHEET_ID = "1oA81zi_TIVwzSH61YGoeRcuVYSQ6L_Sjg0rtVUrbuUQ"

client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)
toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY")) # Ensure this is in your env

# Paths
STATE_FILE = "data/scraper_state.json"
TARGETS_FILE = "data/targets.json"
QUEUE_FILE = "data/pending_leads.json"

# ==========================================
# 2. STATE & QUEUE MANAGEMENT
# ==========================================
def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)

# ==========================================
# 3. ENHANCED SOURCING (Blind Spot 2 & 3 Fix)
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
                if any(re.search(kw, title) for kw in pos_keywords) and not any(re.search(kw, title) for kw in neg_keywords):
                    job_url = job.get('jobUrl') if is_ashby else job.get('absolute_url')
                    
                    # FIX BLIND SPOT 2: Greenhouse JD Fetch
                    desc = ""
                    if is_ashby:
                        desc = job.get('descriptionPlain', '')[:1500]
                    else:
                        # Secondary fetch for Greenhouse detail
                        try:
                            detail_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job.get('id')}"
                            detail_resp = fetcher.get(detail_url)
                            if detail_resp.status == 200:
                                desc = detail_resp.json().get('content', '')[:1500]
                        except: desc = "JD Fetch Failed"

                    raw_leads.append({
                        'company': company_name, 'role': job.get('title'),
                        'url': job_url, 'description': desc
                    })
    except: pass
    return raw_leads

def sourcing_cycle(chunk_size=500):
    all_targets = load_json(TARGETS_FILE, [])
    state = load_json(STATE_FILE, {"new_cursor": 0, "rescan_cursor": 0, "day_count": 1})
    fetcher = Fetcher()
    new_found = []
    
    # Discovery Logic (Paced)
    targets_to_scan = all_targets[state['new_cursor']:state['new_cursor']+chunk_size]
    if state['day_count'] > 7:
        targets_to_scan += all_targets[state['rescan_cursor']:state['rescan_cursor']+chunk_size]
    
    print(f"🕵️ Scanning {len(targets_to_scan)} endpoints...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        for batch in executor.map(lambda u: scrape_single_target(url=u, fetcher=fetcher), targets_to_scan):
            new_found.extend(batch)
            
    # Update State
    state['new_cursor'] += chunk_size
    if state['day_count'] > 7: state['rescan_cursor'] += chunk_size
    state['day_count'] += 1
    save_json(STATE_FILE, state)
    
    return new_found

# ==========================================
# 4. EVALUATION & SYNC (Blind Spot 1 & 4 Fix)
# ==========================================
def process_queue(quota=50):
    queue = load_json(QUEUE_FILE, [])
    
    # If queue is low, find more
    if len(queue) < quota:
        queue.extend(sourcing_cycle())
        save_json(QUEUE_FILE, queue)

    print(f"🧠 Queue size: {len(queue)}. Aiming for {quota} matches...")
    matches = []
    processed_indices = []

    for i, lead in enumerate(queue):
        if len(matches) >= quota: break
        
        prompt = f"Role: {lead['role']}\nCompany: {lead['company']}\nJD: {lead['description']}\n\nSTRICT: If NOT PM, Score=1. High Fit PM > 7.\nOutput JSON: {{\"score\": int, \"cluster\": \"str\"}}"
        try:
            resp = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.1, timeout=15)
            data = json.loads(resp.choices[0].message.content.replace("```json", "").replace("```", ""))
            score = data.get('score', 0)
            if score > 7:
                print(f"🔥 MATCH: {lead['company']} - {lead['role']} ({score}/10)")
                matches.append([time.strftime("%Y-%m-%d"), lead['company'], lead['role'], f"{score}/10", "Pending", lead['url'], f"cv-{data.get('cluster', 'core').lower().replace(' ', '-')}.pdf"])
        except: pass
        processed_indices.append(i)

    # FIX BLIND SPOT 1: Save leftovers
    new_queue = [item for idx, item in enumerate(queue) if idx not in processed_indices]
    save_json(QUEUE_FILE, new_queue)
    print(f"💾 Processed {len(processed_indices)} leads. {len(new_queue)} remaining in queue.")

    # FIX BLIND SPOT 4: Auto-Sync via Composio
    if matches:
        print(f"🚀 Syncing {len(matches)} leads to G-Sheet...")
        try:
            toolset.execute_action(action=Action.GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND, params={"spreadsheetId": SHEET_ID, "range": "Sheet1!A:G", "valueInputOption": "USER_ENTERED", "values": matches})
            print("✅ G-Sheet Sync Complete.")
        except Exception as e: print(f"⚠️ Sync Failed: {e}")

if __name__ == "__main__":
    print("=== 🏗️ INDUSTRIAL ENGINE V6 (BULLETPROOF) INITIATED ===")
    process_queue(quota=50)
    print("=== 🏁 PROCESS COMPLETE ===")
