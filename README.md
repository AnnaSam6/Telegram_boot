# MyEnglishBot - Telegram бот для изучения английского языка

## 📋 Описание
Telegram-бот для изучения английских слов с помощью карточек и тестов.

## ✨ Функционал
- 📚 Изучение базовых слов (цвета, местоимения, глаголы)
- 🎮 Интерактивные тесты с 4 вариантами ответов
- ➕ Добавление персональных слов
- 🗑️ Удаление слов из персонального словаря
- 📊 Статистика обучения
- 👤 Индивидуальный прогресс для каждого пользователя

## 🗄️ Структура базы данных

### ER-диаграмма:
```mermaid
erDiagram
    users ||--o{ user_words : "добавляет"
    users ||--o{ learning_stats : "имеет"
    
    users {
        bigint telegram_id
        varchar username
        varchar first_name
        timestamp created_at
    }
    
    base_words {
        int id
        varchar russian
        varchar english
        varchar category
    }
    
    user_words {
        int id
        int user_id
        varchar russian
        varchar english
        timestamp created_at
    }
    
    learning_stats {
        int id
        int user_id
        int word_id
        int correct_answers
        int wrong_answers
    }
