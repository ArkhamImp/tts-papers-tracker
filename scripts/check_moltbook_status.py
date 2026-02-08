import requests
import json
import sys

# Force UTF-8 encoding for stdout (Windows workaround)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')

api_key = "moltbook_sk_Q3kxSftXcpmtmjK8wMA7CgpO8Eq6WMXK"
url = "https://www.moltbook.com/api/v1/agents/status"
headers = {"Authorization": f"Bearer {api_key}"}

try:
    response = requests.get(url, headers=headers, timeout=10)
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
