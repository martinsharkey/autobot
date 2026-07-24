import os
from pathlib import Path

search_paths = [
    Path(r"C:\Users\MartinSharkey\.gemini"),
    Path(r"c:\Users\MartinSharkey\Documents\Autobot")
]

for sp in search_paths:
    if sp.exists():
        print(f"Searching {sp}...")
        count = 0
        for root, dirs, files in os.walk(sp):
            for file in files:
                if "feishu" in file.lower() or "telegram" in file.lower():
                    print("-", Path(root) / file)
                    count += 1
                    if count >= 20:
                        break
            if count >= 20:
                break
