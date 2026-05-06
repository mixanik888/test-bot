-- Этап 3: упрощённый конструктор процесса (trigger/action), сохранение и версии
CREATE TABLE IF NOT EXISTS flow_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL UNIQUE,
    draft_schema TEXT NOT NULL DEFAULT '[]',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS flow_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_definition_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    schema TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flow_definition_id) REFERENCES flow_definitions(id) ON DELETE CASCADE
);
