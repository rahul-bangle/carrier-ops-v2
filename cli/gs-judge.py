#!/usr/bin/env python3
import sys
import json
import time
from openai import OpenAI

LOCAL_ENDPOINT = "http://172.24.192.1:8317/v1"
MODEL_NAME = "gemini-3.1-flash-lite-preview"
PROXY_TOKEN = "sk-pro-rahul"

client = OpenAI(base_url=LOCAL_ENDPOINT, api_key=PROXY_TOKEN)

def score_jobs(leads):
    scored_leads = []
    
    for lead in leads:
        prompt = f"""
        Role: {lead['role']}
        Company: {lead['company']}
        JD: {lead['description']}
        
        STRICT RULES:
        1. If NOT a PM role, Score=1.
        2. If the JD requires MORE than 2 years of experience (e.g. "3+ years", "5 years"), Score=1.
        3. LOCATION (GLOBAL-LOCAL HYBRID): 
           - Accept if located in India (Bangalore, Hyderabad, Pune, Mumbai, Delhi, etc.)
           - Accept if explicitly mentions Remote hiring from India/APAC.
           - Accept if company is Global (US/UK/EU) but JD mentions an India office or India-based team.
           - Reject if strictly US/UK/EU ONLY with no India path.
        4. Target: Entry-level/Junior PM (0-1 years). High Fit > 7.
        
        Output JSON: {{"score": int, "cluster": "str", "dm_draft": "str"}}
        """
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME, 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0.1, 
                timeout=15
            )
            content = resp.choices[0].message.content
            
            # Cleanup markdown JSON blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            data = json.loads(content)
            
            lead['ai_eval'] = data
            scored_leads.append(lead)
        except Exception as e:
            print(f"Error scoring {lead['company']}: {e}", file=sys.stderr)
            
    return scored_leads

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        leads = json.loads(input_data)
        scored = score_jobs(leads)
        print(json.dumps(scored, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
