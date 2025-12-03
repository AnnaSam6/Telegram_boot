import os
from dotenv import load_dotenv  # ДОБАВЬТЕ ЭТУ СТРОКУ

load_dotenv()  # ДОБАВЬТЕ ЭТУ СТРОКУ

# Токен бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Проверка наличия токена
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен. Создайте файл .env с переменной BOT_TOKEN")

# ID администраторов (опционально)
ADMIN_IDS = []
admin_ids_str = os.getenv('ADMIN_IDS', '')
if admin_ids_str:
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',')]

# Настройки базы данных
DB_PATH = 'english_learning_bot.db'

# Максимальное количество пользовательских слов
MAX_USER_WORDS = 100

# Настройки квиза
QUIZ_OPTIONS_COUNT = 4
