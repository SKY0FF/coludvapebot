# reset_users.py
from database import db
import sqlite3

print("Сбрасываю таблицу пользователей...")

# Удаляем и создаем заново
db.cursor.execute("DROP TABLE IF EXISTS users")
db.conn.commit()

# Создаем заново
db.cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        is_admin BOOLEAN DEFAULT 0,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
db.conn.commit()

print("✅ Таблица пользователей сброшена!")