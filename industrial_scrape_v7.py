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

# ==========================================
# 1. CONFIGURATION
# ==========================================
LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1" 
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
PROXY_TOKEN = "sk-pro-rahul"
SHEET_ID = "1oA81zi_TIVwzSH61YGoeRcuVYSQ6L_Sjg0rtVUrbuUQ"

client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)

STATE_FILE = "data/scraper_state.json"
TARGETS_FILE = "data/targets.json"
QUEUE_FILE = "data/pending_leads.json"
HISTORY_FILE = "data/job_history.json" # FIX #1 & #8: Track seen URLs & Applications

# ==========================================
# 2. STATE & SOURCING 
# ==========================================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # FIX #2: Atomic write to prevent corruption on crash/HDD lag
    temp_path = f"{path}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as f: 
        json.dump(data, f, indent=2)
    os.replace(temp_path, path)

def is_duplicate_or_applied(job_url: str, history: dict) -> bool:
    # FIX #1 & #8: Skip if URL exists in history (Already Scanned or Applied)
    return job_url in history

def scrape_single_target(url: str, fetcher: Fetcher, history: dict) -> List[Dict]:
    raw_leads = []
    pos_keywords = [r'\bpm\b', r'\bproduct manager\b', r'\bproduct owner\b', r'\bapm\b']
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
                job_url = job.get('jobUrl') if is_ashby else job.get('absolute_url')
                
                # FIX #1 & #8 check
                if is_duplicate_or_applied(job_url, history):
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

                    # FIX #6: Skip if JD fetch failed (Blank or too short)
                    if not desc or len(desc.strip()) < 100:
                        continue 

                    raw_leads.append({
                        'company': company_name, 'role': job.get('title'),
                        'url': job_url, 'description': desc
                    })
    except: pass
    return raw_leads

def sourcing_cycle(chunk_size=500):
    all_targets = load_json(TARGETS_FILE, [])
    state = load_json(STATE_FILE, {"new_cursor": 0, "rescan_cursor": 0, "day_count": 1})
    history = load_json(HISTORY_FILE, {}) # Load history for dedup
    fetcher = Fetcher()
    new_found = []
    
    targets_to_scan = all_targets[state['new_cursor']:state['new_cursor']+chunk_size]
    if state['day_count'] > 7:
        targets_to_scan += all_targets[state['rescan_cursor']:state['rescan_cursor']+chunk_size]
    
    print(f"🕵️ Scanning {len(targets_to_scan)} endpoints...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Pass history to scrape function for early dedup
        for batch in executor.map(lambda u: scrape_single_target(u, fetcher, history), targets_to_scan):
            new_found.extend(batch)
            
    state['new_cursor'] += chunk_size
    if state['day_count'] > 7: state['rescan_cursor'] += chunk_size
    state['day_count'] += 1
    save_json(STATE_FILE, state)
    
    return new_found

# ==========================================
# 3. DORKING (The Sniper)
# ==========================================
def find_contact(company_name: str, fetcher: Fetcher) -> str:
    query = f'site:linkedin.com/in "Head of Product" OR "Founder" "{company_name}"'
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    try:
        response = fetcher.get(search_url)
        if response.status == 200:
            matches = re.findall(r'https://[a-z]{0,2}\.?linkedin\.com/in/[^"\'<&?]+', response.text)
            if matches:
                return matches[0].split('?')[0]
    except: pass
    return "Search Manually"

# ==========================================
# 4. EVALUATION & SYNC (V7.1 - Sector Agnostic)
# ==========================================
def process_queue(quota=50):
    queue = load_json(QUEUE_FILE, [])
    history = load_json(HISTORY_FILE, {}) # For updating history
    
    if len(queue) < quota:
        queue.extend(sourcing_cycle())
        save_json(QUEUE_FILE, queue)

    print(f"🧠 Queue size: {len(queue)}. Aiming for {quota} matches...")
    matches = []
    processed_indices = []
    fetcher = Fetcher()

    for i, lead in enumerate(queue):
        if len(matches) >= quota: break
        
        prompt = f"""
        Role: {lead['role']}
        Company: {lead['company']}
        JD: {lead['description']}
        
        STRICT RULES:
        1. Is this a Product Management role? If NO, Score=1.
        2. Evaluate fit for a generalist PM (Data-driven, execution-focused). 
        3. Provide a hyper-personalized 2-line DM draft to the Hiring Manager mentioning one specific challenge from the JD.
        
        Output JSON: {{"score": int (1-10), "cluster": "str", "dm_draft": "str"}}
        """
        
        try:
            resp = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.1, timeout=15)
            content = resp.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            score = data.get('score', 0)
            
            if score > 7:
                print(f"🔥 MATCH: {lead['company']} - {lead['role']} ({score}/10)")
                contact_link = find_contact(lead['company'], fetcher)
                
                # Appending the new Success Metric columns (Date Applied, First Round Date, Rejection Date)
                matches.append([
                    time.strftime("%Y-%m-%d"), lead['company'], lead['role'], f"{score}/10", "Pending", 
                    lead['url'], f"cv-{data.get('cluster', 'core').lower().replace(' ', '-')}.pdf",
                    contact_link, data.get('dm_draft', 'No draft generated.'),
                    "", "", "" # Empty columns for tracking (FIX #9)
                ])
                
            # Add to history to prevent duplicates in future runs (FIX #1)
            history[lead['url']] = {"status": "scanned", "date": time.strftime("%Y-%m-%d"), "score": score}
                
        except Exception as e: 
            print(f"⚠️ AI Error on {lead['company']}: {e}")
            pass
            
        processed_indices.append(i)

    # Save leftover queue and updated history
    new_queue = [item for idx, item in enumerate(queue) if idx not in processed_indices]
    save_json(QUEUE_FILE, new_queue)
    save_json(HISTORY_FILE, history)
    print(f"💾 Processed {len(processed_indices)} leads. {len(new_queue)} remaining in queue.")

    if matches:
        filename = f"industrial_leads_v7_{time.strftime('%Y%m%d')}.csv"
        print(f"🚀 Saving {len(matches)} leads to {filename}...")
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # FIX #9: Adding tracking columns
            writer.writerow(['Date Found', 'Company', 'Role', 'Score', 'Status', 'URL', 'CV_Type', 'Contact', 'DM_Draft', 'Date Applied', 'Interview Date', 'Rejection Date'])
            writer.writerows(matches)
        print("✅ CSV Export Complete.")

if __name__ == "__main__":
    print("=== 🏗️ INDUSTRIAL ENGINE V7.1 (BULLETPROOF OPS) INITIATED ===")
    process_queue(quota=50)
    print("=== 🏁 PROCESS COMPLETE ===")
