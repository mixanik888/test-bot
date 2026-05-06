-- Этап 3: интеграция MAX (хранение токена и идентификатора бота MAX)
CREATE TABLE IF NOT EXISTS bot_max_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL UNIQUE,
    access_token VARCHAR(255) NOT NULL,
    bot_user_id INTEGER,
    bot_username VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
);
