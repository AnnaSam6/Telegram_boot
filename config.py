"""
Конфигурационный файл бота для изучения английского языка.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле")

# ID администраторов
admin_ids_str = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

# Настройки базы данных
DB_PATH = 'english_vocabulary.db'

# Настройки обучения
QUESTIONS_PER_SESSION = 5
MAX_USER_WORDS = 200
