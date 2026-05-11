import os
import json
import time
import csv
from typing import List, Dict
from openai import OpenAI
from scrapling import Fetcher

# ==========================================
# 1. CONFIGURATION (CLI-PROXY + CSV Only)
# ==========================================

# Using CLI-PROXY from WSL to Windows Host
LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1" 
MODEL_NAME = "gemini-3.1-flash-lite-preview" 
PROXY_TOKEN = "sk-pro-rahul"

# Connect to CLI-PROXY Endpoint
client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)

# ==========================================
# 2. DYNAMIC TARGET GENERATION
# ==========================================
def generate_targets_from_history() -> List[str]:
    print("📂 Analyzing scan-history.tsv for dynamic endpoints...")
    targets = set()
    tsv_path = "data/scan-history.tsv"
    
    if not os.path.exists(tsv_path):
        print(f"⚠️ Warning: {tsv_path} not found. Falling back to defaults.")
        return [
            "https://api.ashbyhq.com/posting-api/job-board/elevenlabs",
            "https://api.ashbyhq.com/posting-api/job-board/bland",
            "https://api.ashbyhq.com/posting-api/job-board/perplexity"
        ]
        
    try:
        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                url = row.get('url', '')
                if 'jobs.ashbyhq.com' in url:
                    parts = url.split('/')
                    if len(parts) >= 4:
                        company_slug = parts[3]
                        targets.add(f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}")
                elif 'boards.greenhouse.io' in url:
                     parts = url.split('/')
                     if len(parts) >= 4:
                         company_slug = parts[3]
                         targets.add(f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs")

        target_list = list(targets)
        print(f"✅ Generated {len(target_list)} unique API endpoints from history.")
        return target_list
    except Exception as e:
        print(f"❌ Error reading history TSV: {e}")
        return []

# ==========================================
# 3. STEALTH SOURCING (Scrapling)
# ==========================================
def scrape_ats_dorks(limit=10) -> List[Dict]:
    print(f"🕵️  Initiating Stealth Scrapling (Test Limit: {limit} endpoints)...")
    fetcher = Fetcher()
    raw_leads = []
    
    all_targets = generate_targets_from_history()
    target_apis = all_targets[:limit] # Safety limit for test
    
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
                    if any(kw in title for kw in ['product manager', 'pm', 'founding pm', 'product owner']):
                        job_url = job.get('jobUrl') if is_ashby else job.get('absolute_url')
                        desc = job.get('descriptionPlain', '')[:1500] if is_ashby else "Greenhouse JD - Filtered by Title"
                        
                        raw_leads.append({
                            'company': company_name,
                            'role': job.get('title'),
                            'url': job_url,
                            'description': desc
                        })
            time.sleep(0.3)
        except Exception as e:
            pass
            
    print(f"✅ Extracted {len(raw_leads)} raw PM leads.")
    return raw_leads

# ==========================================
# 4. FILTERING (Local AI Endpoint: Score > 7)
# ==========================================
def filter_and_tailor(leads: List[Dict]) -> List[List]:
    if not leads:
        return []
        
    print(f"🧠 Passing {len(leads)} leads to AI for Evaluation...")
    approved_rows = []
    
    for lead in leads:
        prompt = f"""
        Role: {lead['role']}
        Company: {lead['company']}
        JD: {lead['description']}
        
        Output strictly valid JSON:
        {{
          "score": integer (1-10),
          "summary": "2-line tailored reason",
          "cluster": "One of ['0-to-1 Builder', 'Scale & Ops', 'Platform PM']"
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=30
            )
            
            result_text = response.choices[0].message.content
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
                
            eval_data = json.loads(result_text)
            score = eval_data.get('score', 0)
            
            if score > 7:
                row = [
                    time.strftime("%Y-%m-%d"),
                    lead['company'],
                    lead['role'],
                    f"{score}/10",
                    "Pending",
                    lead['url'],
                    f"cv-{eval_data.get('cluster', 'core').lower().replace(' ', '-')}.pdf"
                ]
                approved_rows.append(row)
                print(f"🔥 HIGH MATCH ({score}/10): {lead['company']} - {lead['role']}")
            else:
                print(f"❌ Dropped ({score}/10): {lead['company']}")
        except Exception as e:
             print(f"⚠️ AI Error on {lead['company']}: {e}")
             
    return approved_rows

# ==========================================
# 5. CSV EXPORT
# ==========================================
def save_to_csv(rows: List[List]):
    if not rows:
        print("📭 No leads passed the >7 score filter today.")
        return
        
    filename = f"test_leads_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        headers = ['Date', 'Company', 'Role', 'Score', 'Status', 'URL', 'CV_Type']
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"✅ CSV created: {os.path.abspath(filename)}")
    except Exception as e:
        print(f"❌ CSV Export Error: {e}")

if __name__ == "__main__":
    print("=== 🏗️  INDUSTRIAL ENGINE V2 (DYNAMIC) INITIATED ===")
    try:
        raw_leads = scrape_ats_dorks(limit=20) # Testing first 20 endpoints
        tailored_rows = filter_and_tailor(raw_leads)
        save_to_csv(tailored_rows)
        print("=== 🏁 PROCESS COMPLETE ===")
    except Exception as e:
        print(f"💥 Fatal Error: {e}")
