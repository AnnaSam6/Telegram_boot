CREATE_TABLES = """
-- 1. Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Категории слов
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- 3. Общие слова (для всех пользователей)
CREATE TABLE IF NOT EXISTS base_words (
    id SERIAL PRIMARY KEY,
    russian VARCHAR(100) NOT NULL,
    english VARCHAR(100) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    UNIQUE(russian, english)
);

-- 4. Персональные слова пользователей
CREATE TABLE IF NOT EXISTS user_words (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    russian VARCHAR(100) NOT NULL,
    english VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, russian, english)
);

-- 5. Статистика обучения
CREATE TABLE IF NOT EXISTS learning_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    word_id INTEGER,
    word_type VARCHAR(10) CHECK (word_type IN ('base', 'user')),
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    last_practiced TIMESTAMP
);
"""
