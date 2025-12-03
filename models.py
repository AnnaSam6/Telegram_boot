CREATE_TABLES_SQL = """
-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Категории слов (общие для всех)
CREATE TABLE IF NOT EXISTS word_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- Базовые слова (общие для всех пользователей)
CREATE TABLE IF NOT EXISTS base_words (
    id SERIAL PRIMARY KEY,
    russian VARCHAR(100) NOT NULL,
    english VARCHAR(100) NOT NULL,
    category_id INTEGER REFERENCES word_categories(id),
    UNIQUE(russian, english)
);

-- Персональные слова пользователей
CREATE TABLE IF NOT EXISTS user_words (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    russian VARCHAR(100) NOT NULL,
    english VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, russian, english)
);

-- Статистика изучения
CREATE TABLE IF NOT EXISTS learning_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    word_id INTEGER,
    word_type VARCHAR(20) CHECK (word_type IN ('base', 'user')),
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    last_practiced TIMESTAMP,
    UNIQUE(user_id, word_id, word_type)
);
"""

# SQL для заполнения начальными данными
INITIAL_DATA_SQL = """
-- Добавляем категории
INSERT INTO word_categories (name, description) VALUES
('Цвета', 'Основные цвета'),
('Местоимения', 'Личные местоимения'),
('Глаголы', 'Простые глаголы'),
('Прилагательные', 'Основные прилагательные'),
('Существительные', 'Простые существительные')
ON CONFLICT (name) DO NOTHING;

-- Добавляем базовые слова
INSERT INTO base_words (russian, english, category_id) VALUES
-- Цвета
('красный', 'red', 1),
('синий', 'blue', 1),
('зеленый', 'green', 1),
('желтый', 'yellow', 1),
('черный', 'black', 1),
('белый', 'white', 1),
('коричневый', 'brown', 1),
('оранжевый', 'orange', 1),
('розовый', 'pink', 1),
('фиолетовый', 'purple', 1),
-- Местоимения
('я', 'I', 2),
('ты', 'you', 2),
('он', 'he', 2),
('она', 'she', 2),
('оно', 'it', 2),
('мы', 'we', 2),
('вы', 'you', 2),
('они', 'they', 2),
-- Глаголы
('быть', 'be', 3),
('иметь', 'have', 3),
('делать', 'do', 3),
('идти', 'go', 3),
('видеть', 'see', 3),
('знать', 'know', 3),
('хотеть', 'want', 3),
('любить', 'love', 3),
('говорить', 'speak', 3),
('учиться', 'learn', 3)
ON CONFLICT (russian, english) DO NOTHING;
"""
