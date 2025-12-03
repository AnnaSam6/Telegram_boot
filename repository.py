"""
Репозиторий для работы с данными.
Содержит все необходимые методы для взаимодействия с БД.
"""

import logging
import random
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from database import Database

logger = logging.getLogger(__name__)


class Repository:
    """Репозиторий для работы с данными бота."""
    
    def __init__(self):
        """Инициализация репозитория."""
        self.db = Database()
    
    # === Методы для пользователей ===
    
    def add_user(self, user_id: int, username: str = None,
                 first_name: str = None, last_name: str = None) -> bool:
        """
        Добавление нового пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            username: Имя пользователя (опционально)
            first_name: Имя (опционально)
            last_name: Фамилия (опционально)
            
        Returns:
            True если пользователь добавлен, False если уже существует
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование пользователя
                cursor.execute(
                    "SELECT 1 FROM users WHERE user_id = ?",
                    (user_id,)
                )
                if cursor.fetchone():
                    return False
                
                # Добавляем пользователя
                cursor.execute(
                    """
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, username, first_name, last_name)
                )
                logger.info(f"Добавлен пользователь: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
    
    # === Методы для слов ===
    
    def get_random_standard_word(self) -> Optional[Dict]:
        """Получение случайного стандартного слова."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, english, russian, category 
                    FROM standard_words 
                    ORDER BY RANDOM() 
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении случайного слова: {e}")
            return None
    
    def get_random_word_options(self, correct_word: Dict, count: int = 4) -> List[Dict]:
        """
        Получение вариантов ответов для квиза.
        
        Args:
            correct_word: Правильное слово
            count: Количество вариантов (включая правильный)
            
        Returns:
            Список слов-вариантов
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем случайные слова (кроме правильного)
                cursor.execute(
                    """
                    SELECT english, russian 
                    FROM standard_words 
                    WHERE english != ? 
                    ORDER BY RANDOM() 
                    LIMIT ?
                    """,
                    (correct_word['english'], count - 1)
                )
                
                options = [dict(row) for row in cursor.fetchall()]
                
                # Добавляем правильное слово
                options.append({
                    'english': correct_word['english'],
                    'russian': correct_word['russian']
                })
                
                # Перемешиваем варианты
                random.shuffle(options)
                return options
                
        except Exception as e:
            logger.error(f"Ошибка при получении вариантов ответов: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """Получение всех категорий стандартных слов."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT category FROM standard_words ORDER BY category"
                )
                return [row['category'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []
    
    # === Методы для пользовательских слов ===
    
    def add_user_word(self, user_id: int, english: str,
                     russian: str, category: str = None) -> Tuple[bool, str]:
        """
        Добавление пользовательского слова.
        
        Args:
            user_id: ID пользователя
            english: Слово на английском
            russian: Перевод на русский
            category: Категория слова (опционально)
            
        Returns:
            (успех, сообщение)
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, не существует ли уже такое слово у пользователя
                cursor.execute(
                    """
                    SELECT 1 FROM user_words 
                    WHERE user_id = ? AND english = ?
                    """,
                    (user_id, english)
                )
                if cursor.fetchone():
                    return False, "Это слово уже есть в вашем словаре"
                
                # Проверяем максимальное количество слов
                cursor.execute(
                    "SELECT COUNT(*) FROM user_words WHERE user_id = ?",
                    (user_id,)
                )
                word_count = cursor.fetchone()[0]
                
                from config import MAX_USER_WORDS
                if word_count >= MAX_USER_WORDS:
                    return False, f"Достигнут лимит слов ({MAX_USER_WORDS})"
                
                # Добавляем слово
                cursor.execute(
                    """
                    INSERT INTO user_words (user_id, english, russian, category)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, english, russian, category)
                )
                
                # Получаем обновленное количество слов
                cursor.execute(
                    "SELECT COUNT(*) FROM user_words WHERE user_id = ?",
                    (user_id,)
                )
                new_count = cursor.fetchone()[0]
                
                logger.info(f"Добавлено слово '{english}' для пользователя {user_id}")
                return True, f"Слово добавлено! Всего слов: {new_count}"
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользовательского слова: {e}")
            return False, f"Ошибка при добавлении слова: {e}"
    
    def delete_user_word(self, user_id: int, english: str) -> Tuple[bool, str]:
        """
        Удаление пользовательского слова.
        
        Args:
            user_id: ID пользователя
            english: Слово на английском
            
        Returns:
            (успех, сообщение)
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    DELETE FROM user_words 
                    WHERE user_id = ? AND english = ?
                    """,
                    (user_id, english)
                )
                
                deleted = cursor.rowcount > 0
                
                if deleted:
                    # Получаем оставшееся количество слов
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_words WHERE user_id = ?",
                        (user_id,)
                    )
                    remaining = cursor.fetchone()[0]
                    
                    logger.info(f"Удалено слово '{english}' у пользователя {user_id}")
                    return True, f"Слово удалено! Осталось слов: {remaining}"
                else:
                    return False, "Слово не найдено в вашем словаре"
                    
        except Exception as e:
            logger.error(f"Ошибка при удалении пользовательского слова: {e}")
            return False, f"Ошибка при удалении слова: {e}"
    
    def get_user_words(self, user_id: int) -> List[Dict]:
        """Получение всех пользовательских слов."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, english, russian, category, created_at
                    FROM user_words 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении пользовательских слов: {e}")
            return []
    
    def get_user_word_count(self, user_id: int) -> int:
        """Получение количества пользовательских слов."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM user_words WHERE user_id = ?",
                    (user_id,)
                )
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка при получении количества слов: {e}")
            return 0
    
    # === Методы для статистики ===
    
    def update_learning_stats(self, user_id: int, word_id: int,
                            word_type: str, is_correct: bool) -> bool:
        """
        Обновление статистики изучения слова.
        
        Args:
            user_id: ID пользователя
            word_id: ID слова
            word_type: Тип слова ('standard' или 'user')
            is_correct: Правильный ли ответ
            
        Returns:
            True если успешно
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now()
                
                # Проверяем существующую запись
                cursor.execute(
                    """
                    SELECT id, correct_answers, total_attempts 
                    FROM learning_stats 
                    WHERE user_id = ? AND word_id = ? AND word_type = ?
                    """,
                    (user_id, word_id, word_type)
                )
                
                existing = cursor.fetchone()
                
                if existing:
                    # Обновляем существующую запись
                    stats_id = existing['id']
                    correct = existing['correct_answers']
                    total = existing['total_attempts']
                    
                    new_correct = correct + (1 if is_correct else 0)
                    new_total = total + 1
                    
                    cursor.execute(
                        """
                        UPDATE learning_stats 
                        SET correct_answers = ?, total_attempts = ?,
                            last_reviewed = ?, next_review = ?
                        WHERE id = ?
                        """,
                        (new_correct, new_total, now, now, stats_id)
                    )
                else:
                    # Создаем новую запись
                    cursor.execute(
                        """
                        INSERT INTO learning_stats 
                        (user_id, word_id, word_type, correct_answers,
                         total_attempts, last_reviewed, next_review)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, word_id, word_type,
                         1 if is_correct else 0, 1, now, now)
                    )
                
                # Обновляем статистику сессии
                today = date.today()
                cursor.execute(
                    """
                    SELECT id FROM learning_sessions 
                    WHERE user_id = ? AND session_date = ?
                    """,
                    (user_id, today)
                )
                
                session = cursor.fetchone()
                
                if session:
                    cursor.execute(
                        """
                        UPDATE learning_sessions 
                        SET total_questions = total_questions + 1,
                            correct_answers = correct_answers + ?
                        WHERE id = ?
                        """,
                        (1 if is_correct else 0, session['id'])
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO learning_sessions 
                        (user_id, session_date, total_questions, correct_answers)
                        VALUES (?, ?, 1, ?)
                        """,
                        (user_id, today, 1 if is_correct else 0)
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {e}")
            return False
    
        def get_wrong_options(self, correct_word, count=3):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT english FROM standard_words WHERE english != ? ORDER BY RANDOM() LIMIT ?",
            (correct_word, count)
        )
        options = [row['english'] for row in cursor.fetchall()]
        conn.close()
        return options
    
    def add_user_word(self, user_id, english, russian, category=None):
        """Добавление пользовательского слова"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO user_words (user_id, english, russian, category) VALUES (?, ?, ?, ?)",
                (user_id, english.lower(), russian, category)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            conn.close()
    
    def delete_user_word(self, user_id, english):
        """Удаление пользовательского слова"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_words WHERE user_id = ? AND english = ?",
            (user_id, english.lower())
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def get_user_words(self, user_id):
        """Получение слов пользователя"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT english, russian, category FROM user_words WHERE user_id = ?",
            (user_id,)
        )
        words = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return words
