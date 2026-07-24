import httpx

def check_models():
    url = "https://openrouter.ai/api/v1/models"
    try:
        resp = httpx.get(url)
        if resp.status_code == 200:
            models = resp.json().get("data", [])
            free_models = [m for m in models if float(m.get("pricing", {}).get("prompt", 0)) == 0.0]
            print("Found free models:")
            for m in free_models[:10]:
                print(f"- ID: {m.get('id')} | Name: {m.get('name')}")
        else:
            print("Failed to fetch models:", resp.status_code)
    except Exception as exc:
        print("Error:", exc)

if __name__ == "__main__":
    check_models()
