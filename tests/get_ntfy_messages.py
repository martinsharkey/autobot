import asyncio
import json
import re
import httpx
from pathlib import Path

async def get_token_from_ntfy():
    url = "https://ntfy.sh/martinsharkey_autobot/json?poll=1"
    print(f"Fetching messages from {url}...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                # Parse lines from latest to oldest
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        msg_text = data.get("message", "")
                        print(f"Found message: {msg_text[:30]}...")
                        # Look for Telegram token regex: \d+:[A-Za-z0-9_-]{35}
                        match = re.search(r"(\d+:[A-Za-z0-9_-]{35})", msg_text)
                        if match:
                            token = match.group(1)
                            print(f"SUCCESS: Extracted Telegram Token: {token[:10]}...{token[-5:]}")
                            # Also search for chat ID if sent (or we can extract user ID from sender data if available, 
                            # but ntfy doesn't have telegram user ID. We can extract any numbers in the message).
                            # Let's search for a chat ID matching typical telegram ID lengths (9-10 digits)
                            chat_match = re.search(r"\b(\d{9,10})\b", msg_text)
                            chat_id = chat_match.group(1) if chat_match else ""
                            
                            # Let's write to .env!
                            env_path = Path(".env")
                            env_content = ""
                            if env_path.exists():
                                env_content = env_path.read_text(encoding="utf-8")
                            
                            # Replace or append TELEGRAM_BOT_TOKEN
                            if "TELEGRAM_BOT_TOKEN=" in env_content:
                                env_content = re.sub(r"TELEGRAM_BOT_TOKEN=.*", f"TELEGRAM_BOT_TOKEN={token}", env_content)
                            else:
                                env_content += f"\nTELEGRAM_BOT_TOKEN={token}"
                                
                            env_path.write_text(env_content, encoding="utf-8")
                            print("Updated .env with TELEGRAM_BOT_TOKEN!")
                            return
                    except Exception as e:
                        print("Error parsing line:", e)
                print("No Telegram token match found in the retrieved messages.")
            else:
                print("Error response from ntfy:", resp.status_code)
    except Exception as exc:
        print("Failed to fetch from ntfy:", exc)

if __name__ == "__main__":
    asyncio.run(get_token_from_ntfy())
