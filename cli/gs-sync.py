#!/usr/bin/env python3
import sys
import json
import os
from supabase import create_client, Client

# Use env vars for Supabase to avoid hardcoding keys, but fallback if needed
# You should set SUPABASE_URL and SUPABASE_KEY in your environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pzasaxdmufmhrxdppsbk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB6YXNheGRtdWZtaHJ4ZHBwc2JrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM5NzQ5NywiZXhwIjoyMDkwOTczNDk3fQ.ZqHBzMgj1Ot8yxl2nZfIdgk7PR0bmWWYp2YF8JyWePk")

def sync_to_supabase(scored_leads):
    if SUPABASE_URL == "YOUR_SUPABASE_URL":
        print("Warning: SUPABASE_URL not set. Printing to stdout instead.", file=sys.stderr)
        print(json.dumps([l for l in scored_leads if l.get('ai_eval', {}).get('score', 0) >= 4], indent=2))
        return
        
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        synced = 0
        for lead in scored_leads:
            eval_data = lead.get('ai_eval', {})
            score = eval_data.get('score', 0)
            
            if score >= 4:
                # Check if exists (simplified)
                # In real scenario, add dedup logic here
                try:
                    supabase.table("leads").upsert({
                        "company": lead['company'], 
                        "role": lead['role'], 
                        "score": f"{score}/10",
                        "url": lead['url'], 
                        "description": lead['description'][:1000], # Trucate for DB
                        "cluster": eval_data.get('cluster', 'Core'), 
                        "dm_draft": eval_data.get('dm_draft', ''),
                        "status": "Pending"
                    }).execute()
                    synced += 1
                except Exception as e:
                    pass
                
        print(json.dumps({"status": "success", "synced_count": synced}))
    except Exception as e:
        print(f"Error syncing to Supabase: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        scored_leads = json.loads(input_data)
        sync_to_supabase(scored_leads)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
