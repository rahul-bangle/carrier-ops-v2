import json
import requests
import concurrent.futures
import subprocess

resolved = json.load(open("/mnt/d/Projects/Workspaces/Carrer-ops-v2/data/resolved_targets.json"))

def parse_jobs(provider, payload, company):
    jobs = []
    if provider == "greenhouse" and isinstance(payload, dict):
        for job in payload.get("jobs", []):
            loc = job.get("location") or {}
            jobs.append({
                "company": company,
                "title": job.get("title", ""),
                "url": job.get("absolute_url", ""),
                "location": loc.get("name", "") if isinstance(loc, dict) else ""
            })
    elif provider == "ashby" and isinstance(payload, dict):
        for job in payload.get("jobs", []):
            jobs.append({
                "company": company,
                "title": job.get("title", ""),
                "url": job.get("jobUrl", ""),
                "location": job.get("location", "")
            })
    elif provider == "lever" and isinstance(payload, list):
        for job in payload:
            loc = job.get("categories", {}).get("location", "")
            jobs.append({
                "company": company,
                "title": job.get("text", ""),
                "url": job.get("hostedUrl", ""),
                "location": loc
            })
    return jobs

pm_keywords = ["product manager", "apm", "associate product manager", "product owner", "junior product manager", "entry level product manager"]
anti_keywords = ["senior", "sr", "sr.", "director", "vp", "vice president", "head", "lead", "principal", "staff", "group", "marketing", "intern", "internship", "founding", "manager of"]

def is_valid_title(title):
    t = title.lower()
    # Tokenize to avoid matching 'sr' in 'sri'
    import re
    tokens = set(re.findall(r'\b\w+\b', t))
    
    has_pm = any(k in t for k in pm_keywords)
    
    # Check exact anti-words
    has_anti = False
    for anti in anti_keywords:
        if re.search(r'\b' + re.escape(anti) + r'\b', t):
            has_anti = True
            break
            
    return has_pm and not has_anti

def process_target(t):
    try:
        url = t.get("api_url")
        if not url: return []
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            all_jobs = parse_jobs(t["provider"], resp.json(), t["company"])
            found = []
            for j in all_jobs:
                if is_valid_title(j["title"]):
                    found.append(j)
            return found
    except: pass
    return []

pm_jobs = []
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(process_target, resolved))

for res in results:
    if res: pm_jobs.extend(res)

with open("/mnt/d/Projects/Workspaces/Carrer-ops-v2/cli/pm_jobs_summary.md", "w") as f:
    f.write(f"# PM Jobs Found ({len(pm_jobs)})\\n\\n")
    for j in pm_jobs:
        f.write(f"- **{j['company']}**: [{j['title']}]({j['url']}) - *{j['location']}*\\n")

subprocess.run(["hermes", "kanban", "create", f"[{len(pm_jobs)}] PM Jobs Discovered", "--body", f"Read /mnt/d/Projects/Workspaces/Carrer-ops-v2/cli/pm_jobs_summary.md for the full list of {len(pm_jobs)} PM jobs synced just now!"])
print(f"Success! Synced {len(pm_jobs)} Product Manager jobs.")
