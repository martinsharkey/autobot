import httpx
from pprint import pprint

url = "http://127.0.0.1:8000/v1/chat/completions"
headers = {
    "Authorization": "Bearer changeme",
    "Content-Type": "application/json",
}
payload = {
    "model": "gateway",
    "messages": [{"role": "user", "content": "ping"}],
}

try:
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    print("status:", resp.status_code)
    print("text:", resp.text)
    try:
        pprint(resp.json())
    except Exception as e:
        print("json failed:", e)
except Exception as exc:
    print("request failed:", exc)
