import httpx

url = "http://127.0.0.1:8000/v1/chat/completions"
headers = {
    "Authorization": "Bearer changeme",
    "Content-Type": "application/json",
}
json = {
    "model": "gateway",
    "messages": [{"role": "user", "content": "ping"}],
}

try:
    resp = httpx.post(url, headers=headers, json=json, timeout=15)
    print(resp.status_code)
    print(resp.text)
    try:
        print(resp.json())
    except Exception as exc:
        print("json error", exc)
except Exception as exc:
    print("request failed", exc)
