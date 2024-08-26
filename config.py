import os

def config_get(key):
    config = {
        'token': os.getenv('TELEGRAM_BOT_TOKEN', '')
    }
    return config.get(key)
