-- Этап 4: состояние диалога для question/ожидания следующего ответа
CREATE TABLE IF NOT EXISTS bot_dialog_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    telegram_chat_id VARCHAR(64) NOT NULL,
    waiting_trigger_block_id VARCHAR(128),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_bot_dialog_states_chat
ON bot_dialog_states (bot_id, telegram_chat_id);
