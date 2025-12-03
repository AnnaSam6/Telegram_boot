import sqlite3

class Database:
    def __init__(self, db_path='english_bot.db'):
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Стандартные слова
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS standard_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english TEXT NOT NULL,
                russian TEXT NOT NULL
            )
        ''')
        
        # 3. Пользовательские слова
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                english TEXT NOT NULL,
                russian TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, english)
            )
        ''')
        
        # Добавляем 10 стандартных слов
        cursor.execute("SELECT COUNT(*) FROM standard_words")
        if cursor.fetchone()[0] == 0:
            words = [
                ("red", "красный"),
                ("blue", "синий"),
                ("green", "зеленый"),
                ("yellow", "желтый"),
                ("cat", "кот"),
                ("dog", "собака"),
                ("house", "дом"),
                ("apple", "яблоко"),
                ("water", "вода"),
                ("book", "книга")
            ]
            cursor.executemany(
                "INSERT INTO standard_words (english, russian) VALUES (?, ?)",
                words
            )
            print("Добавлено 10 стандартных слов")
        
        conn.commit()
        conn.close()
