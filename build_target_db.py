import os
import json
import csv
import requests
from typing import Set, List, Dict
from concurrent.futures import ThreadPoolExecutor

def build_db():
    print("🏗️  Building Master Target Database (Enterprise Edition)...")
    # key: slug, value: company_data
    companies: Dict[str, Dict] = {}

    # 1. Load from scan-history.tsv (Existing Data)
    tsv_path = "data/scan-history.tsv"
    if os.path.exists(tsv_path):
        print("📂 Importing slugs from scan-history.tsv...")
        try:
            with open(tsv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    url = row.get('url', '')
                    slug = None
                    if 'jobs.ashbyhq.com' in url:
                        parts = url.split('/')
                        if len(parts) >= 4: slug = parts[3]
                    elif 'boards.greenhouse.io' in url:
                        parts = url.split('/')
                        if len(parts) >= 4: slug = parts[3]
                    
                    if slug and slug not in companies:
                        companies[slug] = {
                            "company": slug.capitalize(),
                            "slug": slug,
                            "website": None,
                            "careers_candidates": [],
                            "guessed_api_urls": [
                                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                                f"https://api.lever.co/v0/postings/{slug}?mode=json"
                            ]
                        }
        except Exception as e:
            print(f"⚠️  Could not read scan-history.tsv: {e}")

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
                    return r.json()
            except:
                return []
            return []

        # Use ThreadPool to speed up 300+ requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            tag_results = executor.map(process_tag, tag_files)
            for items in tag_results:
                if not isinstance(items, list): continue
                for c in items:
                    slug = c.get('slug')
                    if not slug: continue
                    
                    name = c.get('name') or slug
                    website = c.get('website')
                    
                    # Update or add
                    if slug not in companies or (companies[slug]['website'] is None and website):
                        candidates = []
                        if website:
                            base = website.rstrip('/')
                            candidates = [
                                base + "/careers",
                                base + "/jobs",
                                base + "/company/careers",
                                base + "/about/careers",
                                base + "/join-us",
                                base + "/hiring",
                                base + "/join"
                            ]

                        companies[slug] = {
                            "company": name,
                            "slug": slug,
                            "website": website,
                            "careers_candidates": candidates,
                            "guessed_api_urls": [
                                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                                f"https://api.lever.co/v0/postings/{slug}?mode=json"
                            ]
                        }

    # 3. Save to targets_input.json
    output_path = "data/targets_input.json"
    os.makedirs("data", exist_ok=True)
    
    final_list = list(companies.values())
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=2)
        
    print(f"✅ Database Built! Total Unique Companies: {len(final_list)}")
    print(f"📄 Saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    build_db()
