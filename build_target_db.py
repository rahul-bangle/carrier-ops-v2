import os
import json
import csv
import requests
from typing import Set, List
from concurrent.futures import ThreadPoolExecutor

def build_db():
    print("🏗️  Building Master Target Database (Enterprise Edition)...")
    targets = {
        "ashby": set(),
        "greenhouse": set()
    }
    
    # 1. Load from scan-history.tsv (Existing Data)
    tsv_path = "data/scan-history.tsv"
    if os.path.exists(tsv_path):
        print("📂 Importing slugs from scan-history.tsv...")
        with open(tsv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                url = row.get('url', '')
                if 'jobs.ashbyhq.com' in url:
                    parts = url.split('/')
                    if len(parts) >= 4: targets["ashby"].add(parts[3])
                elif 'boards.greenhouse.io' in url:
                    parts = url.split('/')
                    if len(parts) >= 4: targets["greenhouse"].add(parts[3])

    # 2. Fetch from YC-OSS API Repo (Massive Goldmine)
    print("🌐 Mining 5000+ YC startups from yc-oss dataset...")
    
    def fetch_tags():
        # This URL returns the list of all tag files in the repo
        tags_api_url = "https://api.github.com/repos/yc-oss/api/contents/tags"
        try:
            r = requests.get(tags_api_url, timeout=10)
            if r.status_code == 200:
                return r.json()
        except:
            return []
        return []

    tag_files = fetch_tags()
    if tag_files:
        print(f"📦 Found {len(tag_files)} tag categories. Processing in parallel...")
        
        def process_tag(tag_file):
            download_url = tag_file['download_url']
            try:
                r = requests.get(download_url, timeout=10)
                if r.status_code == 200:
                    companies = r.json()
                    local_slugs = []
                    for c in companies:
                        if 'slug' in c:
                            local_slugs.append(c['slug'])
                    return local_slugs
            except:
                return []
            return []

        # Use ThreadPool to speed up 300+ requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(process_tag, tag_files)
            for slugs in results:
                for slug in slugs:
                    targets["ashby"].add(slug)
                    targets["greenhouse"].add(slug)

    # 3. Generate API Endpoints
    final_apis = []
    for slug in targets["ashby"]:
        final_apis.append(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for slug in targets["greenhouse"]:
        final_apis.append(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")

    # 4. Save to targets.json
    output_path = "data/targets.json"
    os.makedirs("data", exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_apis, f, indent=2)
        
    print(f"✅ Database Built! Total Unique Slugs: {len(targets['ashby']) | len(targets['greenhouse'])}")
    print(f"🚀 Total API Endpoints Generated: {len(final_apis)}")
    print(f"📄 Saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    build_db()
