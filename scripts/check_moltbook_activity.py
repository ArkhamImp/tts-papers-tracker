import requests
import json
import sys

# Force UTF-8 encoding for stdout (Windows workaround)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')

api_key = "moltbook_sk_Q3kxSftXcpmtmjK8wMA7CgpO8Eq6WMXK"
base_url = "https://www.moltbook.com/api/v1"

headers = {"Authorization": f"Bearer {api_key}"}

try:
    # Check DMs - requests
    print("=== DM REQUESTS ===")
    response = requests.get(f"{base_url}/agents/dm/requests", headers=headers, timeout=10)
    requests_data = response.json()
    print(json.dumps(requests_data, indent=2, ensure_ascii=False))

    print("\n=== CONVERSATIONS ===")
    response = requests.get(f"{base_url}/agents/dm/conversations", headers=headers, timeout=10)
    conv_data = response.json()
    print(json.dumps(conv_data, indent=2, ensure_ascii=False))

    print("\n=== FEED ===")
    response = requests.get(f"{base_url}/feed?sort=new&limit=5", headers=headers, timeout=10)
    feed_data = response.json()
    print(json.dumps(feed_data, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"Error: {e}")
