import os

def config_get(key):
    config = {
        'token': os.getenv('TELEGRAM_BOT_TOKEN', '7365624478:AAEww_niTdh2E1q9iPS6vxCKgmlM9rXsHp0')
    }
    return config.get(key)