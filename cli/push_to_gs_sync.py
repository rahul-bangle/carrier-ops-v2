import re
import json
import subprocess
import os

with open("/mnt/d/Projects/Workspaces/Carrer-ops-v2/cli/pm_jobs_summary.md", "r", encoding="utf-8") as f:
    text = f.read()

# Since the file might have literal '\n', let's split by both '\n' and '\\n'
text = text.replace("\\n", "\n")
lines = text.split("\n")

leads = []
for line in lines:
    match = re.search(r'- \*\*([^*]+)\*\*: \[([^\]]+)\]\(([^)]+)\) - \*(.*?)\*', line)
    if match:
        leads.append({
            "company": match.group(1).strip(),
            "role": match.group(2).strip(),
            "url": match.group(3).strip(),
            "description": f"Location: {match.group(4).strip()}",
            "ai_eval": {
                "score": 5,
                "cluster": "Core PM",
                "dm_draft": ""
            }
        })

print(f"Found {len(leads)} jobs to sync.")
if leads:
    json_data = json.dumps(leads)
    process = subprocess.run(
        ["/usr/bin/python3", "/mnt/d/Projects/Workspaces/Carrer-ops-v2/cli/gs-sync.py"],
        input=json_data, text=True, capture_output=True, env=os.environ
    )
    print("STDOUT:", process.stdout)
    if process.stderr:
        print("STDERR:", process.stderr)
