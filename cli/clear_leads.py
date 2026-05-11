import os
import re
from supabase import create_client, Client

with open('/mnt/d/Projects/Workspaces/Carrer-ops-v2/cli/gs-sync.py', 'r') as f:
    content = f.read()
    match = re.search(r'SUPABASE_KEY = os.environ.get\("SUPABASE_KEY", "(.*?)"\)', content)
    if match:
        SUPABASE_URL = "https://pzasaxdmufmhrxdppsbk.supabase.co"
        SUPABASE_KEY = match.group(1)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # In Supabase python, to delete all rows we can use a filter that is always true
        # e.g., filter by a column that is not null. url is not null.
        try:
            res = supabase.table("leads").delete().neq("status", "IMPOSSIBLE_VALUE").execute()
            print(f"Deleted old leads. Count: {len(res.data)}")
        except Exception as e:
            print(f"Error deleting: {e}")
    else:
        print("Could not find key")
