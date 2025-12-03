# MyEnglishBot - Telegram бот для изучения английского языка

## 📋 Описание
Telegram-бот для изучения английских слов с PostgreSQL базой данных.

## ✨ Функционал
- 📚 10 базовых слов для всех пользователей (цвета, местоимения)
- 🎮 Тесты с 4 вариантами ответов
- ➕ Добавление персональных слов
- 🗑️ Удаление слов (только своих)
- 📊 Статистика обучения
- 👤 Индивидуальный словарь для каждого пользователя

## 🗄️ Структура базы данных

### ER-диаграмма:
```mermaid
erDiagram
    users ||--o{ user_words : "имеет"
    users ||--o{ learning_stats : "отслеживает"
    
    users {
        int id PK
        bigint telegram_id
        varchar username
        timestamp created_at
    }
    
    base_words {
        int id PK
        varchar russian
        varchar english
    }
    
    user_words {
        int id PK
        int user_id FK
        varchar russian
        varchar english
        timestamp created_at
    }
    
    learning_stats {
        int id PK
        int user_id FK
        int correct_answers
        int wrong_answers
        timestamp last_active
    }
