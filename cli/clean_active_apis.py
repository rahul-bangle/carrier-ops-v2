import asyncio
import aiohttp
import json
import os
from pathlib import Path
from typing import List, Dict

# Increase these if you want more speed, decrease if you get rate limited
CONCURRENCY_LIMIT = 100 
TIMEOUT = 15

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "targets.json"
OUTPUT_FILE = ROOT / "data" / "verified_active_apis.json"

async def check_api(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        try:
            async with session.get(url, timeout=TIMEOUT) as response:
                if response.status == 200:
                    # Quick check if it's actually JSON and not an HTML error page
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "json" in content_type:
                        try:
                            # Minimal peek to ensure it's valid JSON
                            await response.json()
                            return url
                        except:
                            pass
        except Exception:
            pass
    return None

async def main():
    print(f"🧹 Starting Massive API Cleanup...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = json.load(f)

    print(f"📂 Loaded {len(urls)} target URLs. Starting validation...")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY_LIMIT, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_api(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

    active_urls = [url for url in results if url is not None]

    os.makedirs(OUTPUT_FILE.parent, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(active_urls, f, indent=2)

    print(f"\n✅ Cleanup Complete!")
    print(f"📊 Total APIs scanned: {len(urls)}")
    print(f"✨ Total Active APIs found: {len(active_urls)}")
    print(f"📄 Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
