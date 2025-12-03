import random
from database import Database

class LearningService:
    def __init__(self):
        self.db = Database()
    
    def get_question(self, telegram_id):
        """Получение вопроса с вариантами ответов"""
        # Получаем пользователя
        user = self.db.get_user(telegram_id)
        
        # Получаем слова для вопроса
        words = self.db.get_words_for_learning(user['id'], limit=4)
        
        if not words:
            return None
        
        # Выбираем правильное слово
        correct_word = random.choice(words)
        
        # Формируем варианты ответов
        options = [word['english'] for word in words]
        random.shuffle(options)
        
        return {
            'user_id': user['id'],
            'word_id': correct_word['id'],
            'word_type': correct_word['word_type'],
            'question': f"Как переводится слово: <b>{correct_word['russian']}</b>?",
            'options': options,
            'correct_answer': correct_word['english']
        }
    
    def check_answer(self, user_id, word_id, word_type, answer):
        """Проверка ответа"""
        # Получаем слово из БД
        if word_type == 'base':
            query = "SELECT english FROM base_words WHERE id = %s"
        else:
            query = "SELECT english FROM user_words WHERE id = %s"
        
        word = self.db.execute_query(query, (word_id,), fetchone=True)
        
        if not word:
            return False
        
        is_correct = word['english'].lower() == answer.lower()
        
        # Обновляем статистику
        self.db.update_learning_stats(user_id, word_id, word_type, is_correct)
        
        return is_correct
    
    def add_personal_word(self, telegram_id, russian, english):
        """Добавление персонального слова"""
        user = self.db.get_user(telegram_id)
        return self.db.add_user_word(user['id'], russian, english)
    
    def delete_personal_word(self, telegram_id, word_id):
        """Удаление персонального слова"""
        user = self.db.get_user(telegram_id)
        return self.db.delete_user_word(user['id'], word_id)
    
    def get_personal_words_count(self, telegram_id):
        """Получение количества персональных слов"""
        user = self.db.get_user(telegram_id)
        return self.db.get_user_words_count(user['id'])
