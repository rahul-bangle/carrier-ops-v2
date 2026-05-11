
import os
import json
from supabase import create_client, Client

# Credentials from industrial_scrape_v8_supabase.py
SUPABASE_URL = "https://pzasaxdmufmhrxdppsbk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB6YXNheGRtdWZtaHJ4ZHBwc2JrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM5NzQ5NywiZXhwIjoyMDkwOTczNDk3fQ.ZqHBzMgj1Ot8yxl2nZfIdgk7PR0bmWWYp2YF8JyWePk"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def cleanup():
    print("🧹 Starting Database Cleanup...")
    try:
        # Delete all leads (using a filter that matches everything)
        res_leads = supabase.table("leads").delete().neq("status", "ThisWillNeverMatch").execute()
        print(f"✅ Leads cleared.")
        
        # Delete all stats
        res_stats = supabase.table("daily_stats").delete().neq("date", "1900-01-01").execute()
        print(f"✅ Daily Stats cleared.")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup()
