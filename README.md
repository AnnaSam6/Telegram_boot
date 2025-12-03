# 🤖 English Learning Telegram Bot

Telegram бот для изучения английских слов с функцией квизов, добавления пользовательских слов и отслеживания прогресса.

## ✨ Функционал

- 📚 Изучение слов через квизы с 4 вариантами ответа
- ✏️ Добавление собственных слов в личный словарь
- 🗑️ Удаление слов из личного словаря
- 📊 Отслеживание статистики обучения
- 🎯 Разделение слов по категориям
- 👤 Персонализированное хранение данных

## 🏗️ Архитектура проекта

### Схема базы данных

```mermaid
erDiagram
    users ||--o{ user_words : "имеет"
    users ||--o{ learning_stats : "имеет"
    users ||--o{ learning_sessions : "имеет"
    standard_words ||--o{ learning_stats : "используется"
    
    users {
        integer user_id PK
        text username
        text first_name
        text last_name
        timestamp created_at
    }
    
    standard_words {
        integer id PK
        text english UK
        text russian
        text category
        integer difficulty
    }
    
    user_words {
        integer id PK
        integer user_id FK
        text english
        text russian
        text category
        boolean mastered
        timestamp created_at
    }
    
    learning_stats {
        integer id PK
        integer user_id FK
        integer word_id
        text word_type
        integer correct_answers
        integer total_attempts
        timestamp last_reviewed
        timestamp next_review
    }
    
    learning_sessions {
        integer id PK
        integer user_id FK
        date session_date
        integer words_learned
        integer correct_answers
        integer total_questions
    }
