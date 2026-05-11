import asyncio
import aiohttp
import os

async def check_url(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 404:
                    return url
        except Exception:
            # Ignore connection errors, timeouts, etc.
            pass
    return None

async def main():
    input_file = 'apis.txt'
    output_file = '404_errors.txt'
    concurrency_limit = 100

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async with aiohttp.ClientSession() as session:
        tasks = [check_url(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

    errors_404 = [url for url in results if url is not None]

    with open(output_file, 'w') as f:
        for url in errors_404:
            f.write(f"{url}\n")

    print(f"Total 404 errors: {len(errors_404)}")

if __name__ == "__main__":
    asyncio.run(main())
