try:
    import telegram_platform
    print("Telegram platform path:", telegram_platform.__file__)
except Exception as e:
    print("Failed to import telegram_platform:", e)

try:
    import feishu_platform
    print("Feishu platform path:", feishu_platform.__file__)
except Exception as e:
    print("Failed to import feishu_platform:", e)
