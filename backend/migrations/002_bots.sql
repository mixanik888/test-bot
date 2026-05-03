-- Этап 2: боты и лог сообщений Telegram (дублирует SQLAlchemy create_all для документации)

CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    webhook_secret VARCHAR(64) NOT NULL UNIQUE,
    telegram_bot_token VARCHAR(255),
    telegram_bot_username VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS ix_bots_webhook_secret ON bots (webhook_secret);
CREATE INDEX IF NOT EXISTS ix_bots_organization_id ON bots (organization_id);

CREATE TABLE IF NOT EXISTS bot_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    direction VARCHAR(8) NOT NULL,
    telegram_chat_id VARCHAR(64) NOT NULL,
    text VARCHAR(4096),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id)
);

CREATE INDEX IF NOT EXISTS ix_bot_messages_bot_id ON bot_messages (bot_id);
