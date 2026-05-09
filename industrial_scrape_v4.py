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
# 2. TARGET LOADING
# ==========================================
def load_targets() -> List[str]:
    path = "data/targets.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
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

def scrape_all_targets(limit=100):
    print(f"🕵️  Initiating Parallel Sourcing (Limit: {limit} endpoints)...")
    all_targets = load_targets()
    target_apis = all_targets[:limit]
    
    fetcher = Fetcher()
    all_leads = []
    
    # Process in batches of 20 to avoid overwhelming network
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(lambda url: scrape_single_target(url, fetcher), target_apis)
        for batch in results:
            all_leads.extend(batch)
            
    print(f"✅ Extracted {len(all_leads)} PURE PM leads from {limit} companies.")
    return all_leads

# ==========================================
# 4. FILTERING (AI Signal)
# ==========================================
def filter_and_tailor(leads: List[Dict]) -> List[List]:
    if not leads: return []
    print(f"🧠 Passing {len(leads)} leads to AI for evaluation...")
    approved_rows = []
    
    def process_lead(lead):
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
                print(f"🔥 MATCH ({score}/10): {lead['company']} - {lead['role']}")
                return [time.strftime("%Y-%m-%d"), lead['company'], lead['role'], f"{score}/10", "Pending", lead['url'], f"cv-{eval_data.get('cluster', 'core').lower().replace(' ', '-')}.pdf"]
        except:
            pass
        return None

    # Also parallelize AI calls for speed
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(process_lead, leads)
        for res in results:
            if res: approved_rows.append(res)
            
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
    print("=== 🏗️  INDUSTRIAL ENGINE V4 (PARALLEL) INITIATED ===")
    start_time = time.time()
    
    # User can change limit here (e.g., 500 for a real run)
    raw_leads = scrape_all_targets(limit=100) 
    tailored_rows = filter_and_tailor(raw_leads)
    save_to_csv(tailored_rows)
    
    end_time = time.time()
    print(f"=== 🏁 PROCESS COMPLETE IN {int(end_time - start_time)}s ===")
