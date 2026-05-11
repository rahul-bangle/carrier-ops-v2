
import json

# Top Indian startups across sectors using Greenhouse/Ashby/Lever
india_targets = [
    # --- GREENHOUSE ---
    "https://boards-api.greenhouse.io/v1/boards/zomato/jobs",
    "https://boards-api.greenhouse.io/v1/boards/swiggy/jobs",
    "https://boards-api.greenhouse.io/v1/boards/zepto/jobs",
    "https://boards-api.greenhouse.io/v1/boards/cred/jobs",
    "https://boards-api.greenhouse.io/v1/boards/razorpay/jobs",
    "https://boards-api.greenhouse.io/v1/boards/groww/jobs",
    "https://boards-api.greenhouse.io/v1/boards/meesho/jobs",
    "https://boards-api.greenhouse.io/v1/boards/nykaa/jobs",
    "https://boards-api.greenhouse.io/v1/boards/postman/jobs",
    "https://boards-api.greenhouse.io/v1/boards/browserstack/jobs",
    "https://boards-api.greenhouse.io/v1/boards/unacademy/jobs",
    "https://boards-api.greenhouse.io/v1/boards/slice/jobs",
    "https://boards-api.greenhouse.io/v1/boards/jupiter/jobs",
    "https://boards-api.greenhouse.io/v1/boards/upgrad/jobs",
    "https://boards-api.greenhouse.io/v1/boards/headout/jobs",
    "https://boards-api.greenhouse.io/v1/boards/lenskart/jobs",
    "https://boards-api.greenhouse.io/v1/boards/blinkit/jobs",
    "https://boards-api.greenhouse.io/v1/boards/physicswallah/jobs",
    "https://boards-api.greenhouse.io/v1/boards/makemytrip/jobs",
    "https://boards-api.greenhouse.io/v1/boards/chargebee/jobs",
    
    # --- ASHBY ---
    "https://api.ashbyhq.com/posting-api/job-board/elevenlabs",
    "https://api.ashbyhq.com/posting-api/job-board/notion",
    "https://api.ashbyhq.com/posting-api/job-board/figma",
    "https://api.ashbyhq.com/posting-api/job-board/replit",
    "https://api.ashbyhq.com/posting-api/job-board/deel",
    "https://api.ashbyhq.com/posting-api/job-board/posthog",
    "https://api.ashbyhq.com/posting-api/job-board/linear",
    "https://api.ashbyhq.com/posting-api/job-board/vanta",
    "https://api.ashbyhq.com/posting-api/job-board/ambient-ai",
    "https://api.ashbyhq.com/posting-api/job-board/wokelo",
    "https://api.ashbyhq.com/posting-api/job-board/cartesia",
    "https://api.ashbyhq.com/posting-api/job-board/pulsora",
    "https://api.ashbyhq.com/posting-api/job-board/marketfeed",
    "https://api.ashbyhq.com/posting-api/job-board/altura",
    
    # --- LEVER ---
    "https://api.lever.co/v0/postings/paytm?group=team&mode=json",
    "https://api.lever.co/v0/postings/open?group=team&mode=json",
    "https://api.lever.co/v0/postings/yubi?group=team&mode=json",
    "https://api.lever.co/v0/postings/perfios?group=team&mode=json",
    "https://api.lever.co/v0/postings/uniphore?group=team&mode=json",
    "https://api.lever.co/v0/postings/harness?group=team&mode=json",
    "https://api.lever.co/v0/postings/xpressbees?group=team&mode=json",
    "https://api.lever.co/v0/postings/livspace?group=team&mode=json",
    "https://api.lever.co/v0/postings/loophealth?group=team&mode=json",
    "https://api.lever.co/v0/postings/games24x7?group=team&mode=json"
]

def update_targets():
    target_file = "data/targets.json"
    try:
        with open(target_file, 'r') as f:
            existing = json.load(f)
    except:
        existing = []
        
    # Put India targets at the very beginning to prioritize them
    updated = list(set(india_targets + existing))
    
    # Sort so that india_targets are indeed at the top
    # We'll just prepend them to be sure
    final_targets = india_targets + [t for t in existing if t not in india_targets]

    with open(target_file, 'w') as f:
        json.dump(final_targets, f, indent=2)
    print(f"✅ Successfully injected {len(india_targets)} India-specific targets at the top of the list.")

if __name__ == "__main__":
    update_targets()
