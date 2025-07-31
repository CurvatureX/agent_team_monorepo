import os
import sys
import json
import urllib.request
import urllib.parse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)

# Get env vars
supabase_url = os.getenv("SUPABASE_URL")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
test_email = os.getenv("TEST_USER_EMAIL")
test_password = os.getenv("TEST_USER_PASSWORD")

print(f"🔐 Testing authentication...")
print(f"URL: {supabase_url}")
print(f"Email: {test_email}")

# Prepare auth request
auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
headers = {
    "apikey": supabase_anon_key,
    "Content-Type": "application/json",
}
data = json.dumps({
    "email": test_email,
    "password": test_password,
    "gotrue_meta_security": {},
}).encode('utf-8')

# Make auth request
try:
    req = urllib.request.Request(auth_url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        auth_data = json.loads(response.read().decode('utf-8'))
        access_token = auth_data.get("access_token")
        
        if access_token:
            print(f"✅ Got access token: {access_token[:50]}...")
            
            # Test session creation
            session_url = "http://localhost:8000/api/v1/app/sessions"
            session_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            session_data = json.dumps({
                "action": "create",
                "workflow_id": None
            }).encode('utf-8')
            
            print(f"\n📝 Testing session creation...")
            session_req = urllib.request.Request(session_url, data=session_data, headers=session_headers)
            
            try:
                with urllib.request.urlopen(session_req) as session_response:
                    session_result = json.loads(session_response.read().decode('utf-8'))
                    print(f"✅ Session created successfully\!")
                    print(f"Response: {json.dumps(session_result, indent=2)}")
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                print(f"❌ Session creation failed with status {e.code}")
                print(f"Error: {error_body}")
        else:
            print(f"❌ No access token in response")
            print(f"Response: {json.dumps(auth_data, indent=2)}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
