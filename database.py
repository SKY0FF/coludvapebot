# database.py
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = 'vapeshop.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info(f"База данных {db_name} подключена")

    def create_tables(self):
        """Создание всех необходимых таблиц"""
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_bot BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notifications_enabled BOOLEAN DEFAULT 1
            )
        ''')

        # Таблица товаров
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT,
                image_url TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица сообщений для рассылки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS broadcast_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                total_users INTEGER DEFAULT 0,
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        ''')

        self.conn.commit()
        logger.info("Таблицы созданы/проверены")

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ===

    def add_or_update_user(self, user_data: Dict):
        """Добавление или обновление пользователя"""
        try:
            self.cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name, language_code, is_bot, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_activity = excluded.last_activity
            ''', (
                user_data['id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code'),
                user_data.get('is_bot', False),
                datetime.now()
            ))
            self.conn.commit()
            logger.debug(f"Пользователь {user_data['id']} обновлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            return False

    def get_all_users(self, active_only: bool = True) -> List[Dict]:
        """Получение всех пользователей"""
        try:
            query = "SELECT * FROM users"
            if active_only:
                query += " WHERE notifications_enabled = 1"
            
            self.cursor.execute(query)
            users = [dict(row) for row in self.cursor.fetchall()]
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return []

    def get_user_count(self) -> int:
        """Получение количества пользователей"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM users")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете пользователей: {e}")
            return 0

    def get_active_user_count(self) -> int:
        """Получение количества активных пользователей (с включенными уведомлениями)"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM users WHERE notifications_enabled = 1")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете активных пользователей: {e}")
            return 0

    def disable_user_notifications(self, user_id: int) -> bool:
        """Отключение уведомлений для пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET notifications_enabled = 0 WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отключении уведомлений: {e}")
            return False

    def enable_user_notifications(self, user_id: int) -> bool:
        """Включение уведомлений для пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET notifications_enabled = 1 WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при включении уведомлений: {e}")
            return False

    # === МЕТОДЫ ДЛЯ РАБОТЫ С РАССЫЛКОЙ ===

    def save_broadcast_message(self, admin_id: int, message_text: str, total_users: int) -> int:
        """Сохранение информации о рассылке"""
        try:
            self.cursor.execute('''
                INSERT INTO broadcast_messages 
                (admin_id, message_text, total_users, status)
                VALUES (?, ?, ?, ?)
            ''', (admin_id, message_text, total_users, 'pending'))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при сохранении рассылки: {e}")
            return 0

    def update_broadcast_status(self, broadcast_id: int, sent: int = 0, failed: int = 0, status: str = 'completed'):
        """Обновление статуса рассылки"""
        try:
            self.cursor.execute('''
                UPDATE broadcast_messages 
                SET sent_count = sent_count + ?, 
                    failed_count = failed_count + ?,
                    status = ?,
                    sent_at = CASE WHEN status = 'pending' THEN CURRENT_TIMESTAMP ELSE sent_at END
                WHERE id = ?
            ''', (sent, failed, status, broadcast_id))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса рассылки: {e}")

    def get_broadcast_history(self, limit: int = 10) -> List[Dict]:
        """Получение истории рассылок"""
        try:
            self.cursor.execute('''
                SELECT * FROM broadcast_messages 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении истории рассылок: {e}")
            return []

    # === МЕТОДЫ ДЛЯ АДМИНИСТРАТОРОВ ===

    def add_admin(self, user_id: int) -> bool:
        """Добавление администратора"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, is_admin)
                VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET is_admin = 1
            ''', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении администратора: {e}")
            return False

    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        try:
            self.cursor.execute(
                "SELECT is_admin FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            return result['is_admin'] == 1 if result else False
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора: {e}")
            return False

    def get_admins(self) -> List[int]:
        """Получение списка администраторов"""
        try:
            self.cursor.execute("SELECT user_id FROM users WHERE is_admin = 1")
            return [row['user_id'] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении администраторов: {e}")
            return []

    # === ЗАКРЫТИЕ СОЕДИНЕНИЯ ===

    def close(self):
        """Закрытие соединения с базой данных"""
        self.conn.close()
        logger.info("Соединение с базой данных закрыто")

# Создаем глобальный экземпляр базы данных
db = Database()
