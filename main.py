# УДАЛИТЬ эти функции:
def load_words():
def load_user_words(user_id):
def save_user_words(user_id, words):

# ДОБАВИТЬ:
from database import Database

db = Database()

# В обработчике start:
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Сохраняем пользователя в БД
    db.add_user(user.id, user.username, user.first_name)
    # ... остальной код

# В обработчике add_word:
async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Получаем данные из сообщения
    text = update.message.text
    parts = text.split('-')
    
    if len(parts) == 2:
        russian, english = parts[0].strip(), parts[1].strip()
        # Сохраняем в БД
        success = db.add_user_word(user_id, russian, english)
        if success:
            await update.message.reply_text(f"Слово '{russian}' добавлено!")
        else:
            await update.message.reply_text("Ошибка при добавлении слова")
