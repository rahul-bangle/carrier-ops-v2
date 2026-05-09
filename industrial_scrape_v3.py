import os
import json
import time
import csv
import re
from typing import List, Dict
from openai import OpenAI
from scrapling import Fetcher

# ==========================================
# 1. CONFIGURATION
# ==========================================
LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1" 
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
PROXY_TOKEN = "sk-pro-rahul"

client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)

# ==========================================
# 2. DYNAMIC TARGET GENERATION
# ==========================================
def generate_targets_from_history() -> List[str]:
    print("📂 Analyzing scan-history.tsv for dynamic endpoints...")
    targets = set()
    tsv_path = "data/scan-history.tsv"
    
    if not os.path.exists(tsv_path):
        return [
            "https://api.ashbyhq.com/posting-api/job-board/elevenlabs",
            "https://api.ashbyhq.com/posting-api/job-board/bland"
        ]
        
    try:
        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                url = row.get('url', '')
                if 'jobs.ashbyhq.com' in url:
                    parts = url.split('/')
                    if len(parts) >= 4:
                        targets.add(f"https://api.ashbyhq.com/posting-api/job-board/{parts[3]}")
                elif 'boards.greenhouse.io' in url:
                     parts = url.split('/')
                     if len(parts) >= 4:
                         targets.add(f"https://boards-api.greenhouse.io/v1/boards/{parts[3]}/jobs")

        return list(targets)
    except Exception as e:
        print(f"❌ Error reading history TSV: {e}")
        return []

# ==========================================
# 3. STEALTH SOURCING (With Strict Word Filters)
# ==========================================
def scrape_ats_dorks(limit=10) -> List[Dict]:
    print(f"🕵️  Initiating Stealth Scrapling (Limit: {limit})...")
    fetcher = Fetcher()
    raw_leads = []
    
    all_targets = generate_targets_from_history()
    target_apis = all_targets[:limit]
    
    # 🛑 KEYWORD FIX: Using regex for whole words to avoid "DeveloPMent"
    pos_keywords = [r'\bpm\b', r'\bproduct manager\b', r'\bfounding pm\b', r'\bproduct owner\b']
    neg_keywords = [r'\bsales\b', r'\bdevelopment representative\b', r'\bsdr\b', r'\bbdr\b', r'\bengineer\b', r'\bmarketing\b']

    for url in target_apis:
        try:
            is_ashby = 'ashbyhq' in url
            slug = url.split('/')[-1] if is_ashby else url.split('/')[-2]
            print(f"🔗 Checking {slug}...")
            
            response = fetcher.get(url)
            if response.status == 200:
                data = response.json()
                jobs = data.get('jobs', [])
                company_name = slug.capitalize()
                
                for job in jobs:
                    title = job.get('title', '').lower()
                    
                    # Apply Positive Filter
                    is_pm = any(re.search(kw, title) for kw in pos_keywords)
                    # Apply Negative Filter
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
            time.sleep(0.3)
        except Exception:
            pass
            
    print(f"✅ Extracted {len(raw_leads)} PURE PM leads (Noise filtered out).")
    return raw_leads

# ==========================================
# 4. FILTERING (Iron-Clad AI Prompt)
# ==========================================
def filter_and_tailor(leads: List[Dict]) -> List[List]:
    if not leads: return []
    print(f"🧠 Passing {len(leads)} leads to AI...")
    approved_rows = []
    
    for lead in leads:
        prompt = f"""
        Role: {lead['role']}
        Company: {lead['company']}
        JD: {lead['description']}
        
        IRON-CLAD FILTER:
        - If the role is NOT Product Management (e.g. Sales, SDR, Engineer, Marketing), SCORE = 1.
        - Rahul is a 0-to-1 Builder & Agentic Ops expert. Score > 7 only for high-fit PM roles.
        
        Output valid JSON: {{"score": int, "summary": "str", "cluster": "str"}}
        """
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=20
            )
            
            result_text = response.choices[0].message.content
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            
            eval_data = json.loads(result_text)
            score = eval_data.get('score', 0)
            
            if score > 7:
                row = [time.strftime("%Y-%m-%d"), lead['company'], lead['role'], f"{score}/10", "Pending", lead['url'], f"cv-{eval_data.get('cluster', 'core').lower().replace(' ', '-')}.pdf"]
                approved_rows.append(row)
                print(f"🔥 MATCH ({score}/10): {lead['company']} - {lead['role']}")
            else:
                print(f"❌ Low Fit ({score}/10): {lead['company']} - {lead['role']}")
        except Exception:
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
    print("=== 🏗️  INDUSTRIAL ENGINE V3 (REFINED) INITIATED ===")
    raw_leads = scrape_ats_dorks(limit=40) # Increased to 40 for real signal
    tailored_rows = filter_and_tailor(raw_leads)
    save_to_csv(tailored_rows)
    print("=== 🏁 PROCESS COMPLETE ===")
