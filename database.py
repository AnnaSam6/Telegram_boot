import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
        self.init_database()
    
    def connect(self):
        """Установка соединения с БД"""
        try:
            self.connection = psycopg2.connect(DATABASE_URL)
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def init_database(self):
        """Инициализация БД: создание таблиц и начальных данных"""
        try:
            with self.connection.cursor() as cursor:
                # Создаем таблицы
                from models import CREATE_TABLES_SQL, INITIAL_DATA_SQL
                cursor.execute(CREATE_TABLES_SQL)
                
                # Заполняем начальными данными
                cursor.execute(INITIAL_DATA_SQL)
                
                self.connection.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database initialization error: {e}")
            raise
    
    def execute_query(self, query, params=None, fetchone=False, fetchall=False):
        """Выполнение SQL запроса"""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                if fetchone:
                    return cursor.fetchone()
                elif fetchall:
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Query error: {e}")
            raise
    
    def get_user(self, telegram_id):
        """Получение или создание пользователя"""
        # Проверяем, есть ли пользователь
        user = self.execute_query(
            "SELECT * FROM users WHERE telegram_id = %s",
            (telegram_id,),
            fetchone=True
        )
        
        if not user:
            # Создаем нового пользователя
            self.execute_query(
                """INSERT INTO users (telegram_id) 
                   VALUES (%s) 
                   RETURNING *""",
                (telegram_id,)
            )
            user = self.execute_query(
                "SELECT * FROM users WHERE telegram_id = %s",
                (telegram_id,),
                fetchone=True
            )
        
        return user
    
    def add_user_word(self, user_id, russian, english):
        """Добавление персонального слова пользователя"""
        return self.execute_query(
            """INSERT INTO user_words (user_id, russian, english) 
               VALUES (%s, %s, %s) 
               ON CONFLICT (user_id, russian, english) DO NOTHING""",
            (user_id, russian, english)
        )
    
    def delete_user_word(self, user_id, word_id):
        """Удаление персонального слова пользователя"""
        return self.execute_query(
            "DELETE FROM user_words WHERE id = %s AND user_id = %s",
            (word_id, user_id)
        )
    
    def get_user_words_count(self, user_id):
        """Получение количества слов пользователя"""
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM user_words WHERE user_id = %s",
            (user_id,),
            fetchone=True
        )
        return result['count'] if result else 0
    
    def get_words_for_learning(self, user_id, limit=4):
        """Получение слов для изучения (базовые + пользовательские)"""
        # Базовые слова
        base_words = self.execute_query(
            """SELECT bw.id, bw.russian, bw.english, 'base' as word_type 
               FROM base_words bw
               ORDER BY RANDOM()
               LIMIT %s""",
            (limit,),
            fetchall=True
        )
        
        # Персональные слова пользователя
        user_words = self.execute_query(
            """SELECT uw.id, uw.russian, uw.english, 'user' as word_type 
               FROM user_words uw
               WHERE uw.user_id = %s
               ORDER BY RANDOM()
               LIMIT %s""",
            (user_id, limit),
            fetchall=True
        )
        
        return base_words + user_words
    
    def update_learning_stats(self, user_id, word_id, word_type, is_correct):
        """Обновление статистики изучения"""
        # Проверяем, есть ли запись
        stats = self.execute_query(
            """SELECT * FROM learning_stats 
               WHERE user_id = %s AND word_id = %s AND word_type = %s""",
            (user_id, word_id, word_type),
            fetchone=True
        )
        
        if stats:
            # Обновляем существующую запись
            if is_correct:
                self.execute_query(
                    """UPDATE learning_stats 
                       SET correct_answers = correct_answers + 1, 
                           last_practiced = CURRENT_TIMESTAMP
                       WHERE id = %s""",
                    (stats['id'],)
                )
            else:
                self.execute_query(
                    """UPDATE learning_stats 
                       SET wrong_answers = wrong_answers + 1, 
                           last_practiced = CURRENT_TIMESTAMP
                       WHERE id = %s""",
                    (stats['id'],)
                )
        else:
            # Создаем новую запись
            if is_correct:
                self.execute_query(
                    """INSERT INTO learning_stats 
                       (user_id, word_id, word_type, correct_answers, last_practiced)
                       VALUES (%s, %s, %s, 1, CURRENT_TIMESTAMP)""",
                    (user_id, word_id, word_type)
                )
            else:
                self.execute_query(
                    """INSERT INTO learning_stats 
                       (user_id, word_id, word_type, wrong_answers, last_practiced)
                       VALUES (%s, %s, %s, 1, CURRENT_TIMESTAMP)""",
                    (user_id, word_id, word_type)
                )
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()
