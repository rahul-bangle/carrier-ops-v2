#!/usr/bin/env python3
import sys
import json
import re
import requests

def fetch_jobs(target_urls):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    raw_leads = []
    pos_keywords = [r'\bpm\b', r'\bproduct manager\b', r'\bproduct owner\b', r'\bapm\b', r'\bassociate product manager\b', r'\bjunior product manager\b']
    neg_keywords = [r'\bsales\b', r'\bdevelopment representative\b', r'\bsdr\b', r'\bbdr\b', r'\bengineer\b', r'\bmarketing\b', r'\bsenior\b', r'\bstaff\b', r'\bprincipal\b', r'\blead\b', r'\bvp\b', r'\bhead\b', r'\bdirector\b']
    
    for url in target_urls:
        try:
            is_ashby = 'ashbyhq' in url
            slug = url.split('/')[-1] if is_ashby else url.split('/')[-2]
            response = session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get('jobs', [])
                company_name = slug.capitalize()
                
                for job in jobs:
                    job_url = job.get('jobUrl') if is_ashby else job.get('absolute_url')
                    title = job.get('title', '').lower()
                    
                    if any(re.search(kw, title) for kw in pos_keywords) and not any(re.search(kw, title) for kw in neg_keywords):
                        desc = ""
                        if is_ashby:
                            desc = job.get('descriptionPlain', '')[:1500]
                        else:
                            try:
                                detail_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job.get('id')}"
                                detail_resp = session.get(detail_url)
                                if detail_resp.status_code == 200:
                                    import html
                                    raw_html = detail_resp.json().get('content', '')
                                    desc = re.sub(r'<[^>]+>', '', html.unescape(raw_html))[:1500]
                            except: pass

                        if not desc or len(desc.strip()) < 100:
                            continue 

                        raw_leads.append({
                            'company': company_name, 
                            'role': job.get('title'),
                            'url': job_url, 
                            'description': desc
                        })
        except Exception as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            
    return raw_leads

if __name__ == "__main__":
    # Expect JSON list of URLs from stdin
    try:
        input_data = sys.stdin.read()
        target_urls = json.loads(input_data)
        leads = fetch_jobs(target_urls)
        print(json.dumps(leads, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
