import asyncio
import aiohttp
import json
import os

async def check_url(session, url, semaphore):
    async with semaphore:
        try:
            # Using head might be more efficient, but let's stick to get if 404 is the goal
            async with session.get(url, timeout=10, allow_redirects=True) as response:
                if response.status == 404:
                    return url
        except Exception:
            # We only care about 404s, so ignore other errors (timeouts, connection errors)
            pass
    return None

async def main():
    input_file = '../data/targets.json'
    output_file = '404_errors.txt'
    concurrency_limit = 100

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    urls = []
    for item in data:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            # The user mentioned objects, so we handle them by looking for common URL keys
            for key in ['url', 'endpoint', 'link', 'href']:
                if key in item and isinstance(item[key], str):
                    urls.append(item[key])
                    break
    
    if not urls:
        print("No URLs found in the input file.")
        return

    print(f"Checking {len(urls)} URLs with concurrency limit {concurrency_limit}...")

    semaphore = asyncio.Semaphore(concurrency_limit)
    
    # Using a custom connector to potentially speed up or handle more connections
    connector = aiohttp.TCPConnector(limit=concurrency_limit)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_url(session, url, semaphore) for url in urls]
        # Using gather to run tasks concurrently
        results = await asyncio.gather(*tasks)

    errors_404 = [url for url in results if url is not None]

    with open(output_file, 'w') as f:
        for url in errors_404:
            f.write(f"{url}\n")

    print(f"Total 404 errors: {len(errors_404)}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
