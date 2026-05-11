#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Set
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
RESOLVED_TARGETS_PATH = ROOT / "data" / "resolved_targets.json"
DEAD_TARGETS_PATH = ROOT / "data" / "dead_targets.json"

REQUEST_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)

MANUAL_OVERRIDES: Dict[str, Dict[str, str]] = {
    "razorpay": {
        "company": "Razorpay",
        "careers_url": "https://razorpay.com/jobs/jobs-all/?location=all&department=",
        "provider": "greenhouse",
        "api_url": (
            "https://boards-api.greenhouse.io/v1/boards/"
            "razorpaysoftwareprivatelimited/jobs?content=true"
        ),
        "source": "manual_override",
    }
}

DEFAULT_INDIAN_COMPANIES = [
    {
        "company": "Razorpay",
        "careers_url": "https://razorpay.com/jobs/jobs-all/?location=all&department=",
        "guessed_api_url": "https://boards-api.greenhouse.io/v1/boards/razorpay/jobs",
    },
    {"company": "Groww", "careers_url": "https://groww.in/careers"},
    {"company": "Postman", "careers_url": "https://www.postman.com/company/careers/"},
    {"company": "Slice", "careers_url": "https://www.sliceit.com/careers"},
    {"company": "Zomato", "careers_url": "https://www.zomato.com/careers"},
    {"company": "Swiggy", "careers_url": "https://careers.swiggy.com/"},
    {"company": "Zepto", "careers_url": "https://www.zeptonow.com/careers"},
    {"company": "Cred", "careers_url": "https://cred.club/careers"},
    {"company": "Meesho", "careers_url": "https://www.meesho.io/jobs"},
    {"company": "Nykaa", "careers_url": "https://www.nykaa.com/careers"},
    {"company": "BrowserStack", "careers_url": "https://www.browserstack.com/careers"},
    {"company": "Unacademy", "careers_url": "https://unacademy.com/careers"},
    {"company": "Jupiter", "careers_url": "https://jupiter.money/careers/"},
    {"company": "upGrad", "careers_url": "https://www.upgrad.com/careers/"},
    {"company": "Headout", "careers_url": "https://www.headout.com/careers/"},
    {"company": "Lenskart", "careers_url": "https://www.lenskart.com/careers"},
    {"company": "Blinkit", "careers_url": "https://blinkit.com/careers"},
    {"company": "Chargebee", "careers_url": "https://www.chargebee.com/careers/"},
    {"company": "Paytm", "careers_url": "https://paytm.com/careers/"},
    {"company": "Yubi", "careers_url": "https://www.go-yubi.com/careers/"},
]


def provider_for_url(url: str) -> Optional[str]:
    lower = url.lower()
    if "boards-api.greenhouse.io" in lower or "job-boards.greenhouse.io" in lower:
        return "greenhouse"
    if "api.ashbyhq.com" in lower or "jobs.ashbyhq.com" in lower:
        return "ashby"
    if "api.lever.co" in lower or "jobs.lever.co" in lower:
        return "lever"
    if "myworkdayjobs.com" in lower or "/wday/cxs/" in lower:
        return "workday"
    return None


def normalize_api_url(url: str) -> str:
    url = unescape(url).strip().rstrip("\\")
    url = url.split("#", 1)[0]
    url = url.replace("\\u0026", "&")

    # Greenhouse
    gh_match = re.search(
        r"https://(?:boards-api|boards)\.greenhouse\.io/(?:v1/boards/)?([^/?#\"'`]+)",
        url,
    )
    if gh_match:
        board = gh_match.group(1).rstrip("/")
        if board == "v1": 
             board = url.split("/")[-1].split("?")[0]
        if "/" in board:
            board = board.split("/")[0]
        query = ""
        if "?" in url:
            query = "?" + url.split("?", 1)[1]
        if "content=true" not in query:
            query = (query + "&content=true") if query else "?content=true"
        return f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs{query.replace('?&', '?')}"

    # Ashby
    ashby_match = re.search(r"https://(?:api|jobs)\.ashbyhq\.com/(?:posting-api/job-board/)?([^/?#\"'`]+)", url)
    if ashby_match:
        return f"https://api.ashbyhq.com/posting-api/job-board/{ashby_match.group(1)}"

    # Lever
    lever_match = re.search(r"https://(?:api|jobs)\.lever\.co/(?:v0/postings/)?([^/?#\"'`]+)", url)
    if lever_match:
        return f"https://api.lever.co/v0/postings/{lever_match.group(1)}?mode=json"

    return url


def extract_api_urls(text: str) -> List[str]:
    patterns = [
        r"https://boards-api\.greenhouse\.io/v1/boards/[^\"'`<>)\s]+",
        r"https://boards\.greenhouse\.io/[^\"'`<>)\s]+",
        r"https://api\.ashbyhq\.com/posting-api/job-board/[^\"'`<>)\s]+",
        r"https://jobs\.ashbyhq\.com/[^\"'`<>)\s]+",
        r"https://api\.lever\.co/v0/postings/[^\"'`<>)\s]+",
        r"https://jobs\.lever\.co/[^\"'`<>)\s]+",
        r"https://[^\"'`<>)\s]*myworkdayjobs\.com/[^\"'`<>)\s]+",
    ]
    found: List[str] = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            url = normalize_api_url(match.group(0).rstrip(".,;"))
            provider = provider_for_url(url)
            if provider and url not in seen:
                seen.add(url)
                found.append(url)
    gh_token_match = re.search(r'["\']boardToken["\']\s*:\s*["\']([^"\']+)["\']', text)
    if gh_token_match:
        url = normalize_api_url(f"https://boards-api.greenhouse.io/v1/boards/{gh_token_match.group(1)}/jobs")
        if url not in seen:
            seen.add(url)
            found.append(url)
    return found


def extract_next_data_urls(html: str) -> List[str]:
    urls = []
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
    if match:
        try:
            data = json.loads(match.group(1))
            def find_urls(obj):
                if isinstance(obj, str):
                    if any(x in obj for x in ["greenhouse.io", "ashbyhq.com", "lever.co"]):
                        urls.extend(extract_api_urls(obj))
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in ["boardToken", "jobBoardToken"]:
                            urls.append(normalize_api_url(f"https://boards-api.greenhouse.io/v1/boards/{v}/jobs"))
                        find_urls(v)
                elif isinstance(obj, list):
                    for item in obj: find_urls(item)
            find_urls(data)
        except: pass
    return urls


def extract_script_urls(page_url: str, html: str) -> List[str]:
    scripts = []
    for match in re.finditer(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.I):
        scripts.append(urljoin(page_url, unescape(match.group(1))))
    return scripts


def parse_jobs(provider: str, payload: Any, company: str) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    if provider == "greenhouse" and isinstance(payload, dict):
        for job in payload.get("jobs", []):
            location = job.get("location") or {}
            jobs.append({
                "company": company,
                "title": job.get("title", ""),
                "url": job.get("absolute_url", ""),
                "location": location.get("name", "") if isinstance(location, dict) else "",
            })
    elif provider == "ashby" and isinstance(payload, dict):
        for job in payload.get("jobs", []):
            jobs.append({
                "company": company,
                "title": job.get("title", ""),
                "url": job.get("jobUrl", ""),
                "location": str(job.get("location") or ""),
            })
    elif provider == "lever" and isinstance(payload, list):
        for job in payload:
            categories = job.get("categories") or {}
            jobs.append({
                "company": company,
                "title": job.get("text", ""),
                "url": job.get("hostedUrl") or job.get("applyUrl") or "",
                "location": categories.get("location", ""),
            })
    return [job for job in jobs if job.get("title") and job.get("url")]


def session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    return sess


def fetch_text(sess: requests.Session, url: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        response = sess.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if response.status_code >= 400:
            return None, f"HTTP {response.status_code}"
        return response.text, None
    except requests.RequestException as exc:
        return None, str(exc)


def validate_api(
    sess: requests.Session, api_url: str, company: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    provider = provider_for_url(api_url)
    if not provider:
        return None, {"reason": "unsupported_provider", "api_url": api_url}
    try:
        response = sess.get(api_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if response.status_code >= 400:
            return None, {"reason": "api_dead", "api_url": api_url, "provider": provider, "status": response.status_code}
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return None, {"reason": "api_dead", "api_url": api_url, "provider": provider, "error": str(exc)}

    jobs = parse_jobs(provider, payload, company)
    if not jobs:
        return None, {"reason": "inactive_company", "api_url": api_url, "provider": provider, "status": response.status_code, "job_count": 0}

    return ({"company": company, "provider": provider, "api_url": api_url, "job_count": len(jobs), "sample_jobs": jobs[:5]}, None)


def discover_api_urls(sess: requests.Session, careers_url: str) -> Tuple[List[str], Optional[str]]:
    html, error = fetch_text(sess, careers_url)
    if html is None: return [], error
    candidates = extract_api_urls(html)
    candidates.extend(extract_next_data_urls(html))
    for script_url in extract_script_urls(careers_url, html):
        script_text, _ = fetch_text(sess, script_url)
        if script_text: candidates.extend(extract_api_urls(script_text))
    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped, None


def resolve_target(target: Dict[str, Any], sess: requests.Session) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    company = target["company"]
    key = target.get("slug", company.lower().strip())
    now = time.strftime("%Y-%m-%d")
    seen = set()
    failures = []

    # 1. Guessed APIs
    guessed_urls = target.get("guessed_api_urls", [])
    if target.get("guessed_api_url"): guessed_urls.append(target["guessed_api_url"])
    for g_url in guessed_urls:
        api_url = normalize_api_url(g_url)
        if api_url in seen: continue
        seen.add(api_url)
        resolved, failure = validate_api(sess, api_url, company)
        if resolved:
            resolved.update({"source": "guessed_api", "last_checked": now})
            return resolved, {}
        if failure: failures.append(failure)

    # 2. Overrides
    override = MANUAL_OVERRIDES.get(key)
    if override:
        api_url = normalize_api_url(override["api_url"])
        if api_url not in seen:
            seen.add(api_url)
            resolved, failure = validate_api(sess, api_url, company)
            if resolved:
                resolved.update({"source": override["source"], "last_checked": now})
                return resolved, {}
            if failure: failures.append(failure)

    # 3. Discovery
    careers_candidates = target.get("careers_candidates", [])
    if target.get("careers_url"):
        if target["careers_url"] not in careers_candidates: careers_candidates.insert(0, target["careers_url"])
    discovered_error = None
    for careers_url in careers_candidates:
        discovered, err = discover_api_urls(sess, careers_url)
        if err: discovered_error = err
        for d_url in discovered:
            d_url = normalize_api_url(d_url)
            if d_url in seen: continue
            seen.add(d_url)
            resolved, failure = validate_api(sess, d_url, company)
            if resolved:
                resolved.update({"careers_url": careers_url, "source": "careers_page", "last_checked": now})
                return resolved, {}
            if failure: failures.append(failure)

    return None, {
        "company": company, "slug": target.get("slug"), "website": target.get("website"),
        "reason": "inactive_company" if careers_candidates else "no_api_found",
        "last_checked": now, "discovery_error": discovered_error, "failures": failures[:5],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

def run(targets: List[Dict[str, Any]], output_path: Path, dead_path: Path, max_workers: int = 15) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    # Resume logic: Load existing results
    resolved = []
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                resolved = json.load(f)
        except: pass
    
    dead = []
    if dead_path.exists():
        try:
            with open(dead_path, "r", encoding="utf-8") as f:
                dead = json.load(f)
        except: pass

    processed_companies = {r["company"] for r in resolved} | {d["company"] for d in dead}
    remaining_targets = [t for t in targets if t["company"] not in processed_companies][:2500]
    
    if not remaining_targets:
        print("✅ All targets already processed.")
        return resolved, dead

    print(f"🚀 Resolving {len(remaining_targets)} remaining targets (Total: {len(targets)}) with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_target = {executor.submit(resolve_target, t, session()): t for t in remaining_targets}
        count = 0
        total = len(remaining_targets)
        for future in as_completed(future_to_target):
            count += 1
            result, failure = future.result()
            if result:
                print(f"[{count}/{total}] OK {result['company']}: {result['job_count']} jobs")
                resolved.append(result)
            else:
                print(f"[{count}/{total}] MISS {failure['company']}: {failure['reason']}")
                dead.append(failure)
            
            # Incremental save every 10 items
            if count % 10 == 0:
                write_json(output_path, resolved)
                write_json(dead_path, dead)
                sys.stdout.flush()

    # Final save
    write_json(output_path, resolved)
    write_json(dead_path, dead)
    return resolved, dead

def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve branded careers pages to real ATS API URLs.")
    parser.add_argument("--input", help="JSON list of targets")
    parser.add_argument("--output", default=str(RESOLVED_TARGETS_PATH))
    parser.add_argument("--dead-output", default=str(DEAD_TARGETS_PATH))
    parser.add_argument("--default-india", action="store_true")
    args = parser.parse_args()

    input_path = args.input or str(RESOLVED_TARGETS_PATH.parent / "targets_input.json")
    if args.default_india:
        targets = DEFAULT_INDIAN_COMPANIES
    else:
        if not os.path.exists(input_path):
            print(f"Error: Input file {input_path} not found.")
            return 1
        with open(input_path, "r", encoding="utf-8") as f:
            targets = json.load(f)

    resolved, dead = run(targets, Path(args.output), Path(args.dead_output))
    print(f"Done! Resolved: {len(resolved)}, Dead: {len(dead)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
