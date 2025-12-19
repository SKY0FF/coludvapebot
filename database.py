# database.py - ПРОСТОЙ И РАБОЧИЙ
import sqlite3
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = 'vapeshop.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables_simple()

        # Инициализируем дефолтные категории только если таблица пустая
        self.initialize_default_categories()

        logger.info(f"✅ База данных подключена: {db_name}")

    def get_moscow_time(self):
        """Получить текущее московское время"""
        utc_now = datetime.utcnow()
        moscow_time = utc_now + timedelta(hours=3)  # UTC+3 для Москвы
        return moscow_time.strftime('%Y-%m-%d %H:%M:%S')

    # database.py - исправляем функцию _create_tables_simple:

    def _create_tables_simple(self):
        """Создание простых таблиц БЕЗ сложных связей"""
        # 1. Пользователи
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS users
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                user_id
                                INTEGER
                                UNIQUE
                                NOT
                                NULL,
                                username
                                TEXT,
                                first_name
                                TEXT,
                                last_name
                                TEXT,
                                is_admin
                                BOOLEAN
                                DEFAULT
                                0,
                                join_date
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            ''')

        # 2. Категории (ПРОСТЫЕ)
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS categories
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                name
                                TEXT
                                NOT
                                NULL
                                UNIQUE,
                                emoji
                                TEXT
                                DEFAULT
                                '📦'
                            )
                            ''')

        # 3. Товары (ПРОСТЫЕ)
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS products
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                category
                                TEXT
                                NOT
                                NULL,
                                name
                                TEXT
                                NOT
                                NULL,
                                price
                                INTEGER
                                NOT
                                NULL,
                                description
                                TEXT,
                                photo_id
                                TEXT,
                                is_active
                                BOOLEAN
                                DEFAULT
                                1
                            )
                            ''')

        # ВАЖНО: УБИРАЕМ АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ ДЕФОЛТНЫХ КАТЕГОРИЙ!
        # Вместо этого добавим функцию для инициализации дефолтных категорий

        self.conn.commit()
        logger.info("✅ Таблицы созданы")

    # Добавим новую функцию для добавления дефолтных категорий только при первом запуске
    def initialize_default_categories(self):
        """Добавить дефолтные категории только если таблица пустая"""
        try:
            # Проверяем, есть ли уже категории
            self.cursor.execute("SELECT COUNT(*) as count FROM categories")
            row = self.cursor.fetchone()

            if row and row['count'] == 0:
                # Таблица пустая, добавляем дефолтные категории
                default_categories = [
                    ('🔋 POD-системы', '🔋'),
                    ('💧 Жидкости', '💧'),
                    ('⚡ Испарители', '⚡'),
                    ('🎒 Аксессуары', '🎒'),
                ]

                for name, emoji in default_categories:
                    self.cursor.execute('''
                                        INSERT
                                        OR IGNORE INTO categories (name, emoji) VALUES (?, ?)
                                        ''', (name, emoji))

                self.conn.commit()
                logger.info("✅ Дефолтные категории добавлены (таблица была пустая)")
                return True
            else:
                logger.info(f"✅ В таблице уже есть {row['count']} категорий, дефолтные не добавляем")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении дефолтных категорий: {e}")
            return False

    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавить или обновить пользователя"""
        try:
            # Получаем текущее московское время
            moscow_time = self.get_moscow_time()

            # Сначала проверяем, существует ли пользователь
            self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            existing_user = self.cursor.fetchone()

            if existing_user:
                # Обновляем существующего пользователя
                self.cursor.execute('''
                                    UPDATE users
                                    SET username   = ?,
                                        first_name = ?,
                                        last_name  = ?,
                                        join_date  = ?
                                    WHERE user_id = ?
                                    ''', (
                                        username or existing_user['username'],
                                        first_name or existing_user['first_name'],
                                        last_name or existing_user['last_name'],
                                        moscow_time,  # Обновляем время тоже
                                        user_id
                                    ))
                logger.info(f"🔄 Пользователь {user_id} обновлен")
            else:
                # Добавляем нового пользователя
                self.cursor.execute('''
                                    INSERT INTO users (user_id, username, first_name, last_name, join_date)
                                    VALUES (?, ?, ?, ?, ?)
                                    ''', (user_id, username, first_name, last_name, moscow_time))
                logger.info(f"✅ Новый пользователь: {first_name} (@{username}) ID: {user_id}")

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении пользователя {user_id}: {e}")
            return False

    def format_moscow_time(self, date_string):
        """Форматировать дату в московское время"""
        if not date_string:
            return "Неизвестно"

        try:
            # Пробуем разные форматы даты
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f'
            ]

            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_string, fmt)
                    break
                except ValueError:
                    continue

            if not dt:
                return date_string  # Возвращаем как есть если не распарсилось

            # Предполагаем что время в БД хранится уже в UTC, конвертируем в MSK
            moscow_dt = dt + timedelta(hours=3)

            # Форматируем по-русски
            return moscow_dt.strftime('%d.%m.%Y в %H:%M')

        except Exception as e:
            logger.error(f"Ошибка форматирования даты {date_string}: {e}")
            return date_string

    def is_admin(self, user_id: int) -> bool:
        try:
            self.cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
            row = self.cursor.fetchone()
            return row and row['is_admin'] == 1
        except:
            return False

    def add_admin(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Добавить или назначить администратора"""
        try:
            moscow_time = self.get_moscow_time()

            # Проверяем, существует ли пользователь
            self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            existing_user = self.cursor.fetchone()

            if existing_user:
                # Обновляем существующего пользователя, назначаем админом
                self.cursor.execute('''
                                    UPDATE users
                                    SET is_admin   = 1,
                                        username   = COALESCE(?, username),
                                        first_name = COALESCE(?, first_name),
                                        last_name  = COALESCE(?, last_name)
                                    WHERE user_id = ?
                                    ''', (username, first_name, last_name, user_id))
                logger.info(f"👑 Назначен администратор: {user_id}")
            else:
                # Добавляем нового пользователя как админа
                self.cursor.execute('''
                                    INSERT INTO users (user_id, username, first_name, last_name, is_admin, join_date)
                                    VALUES (?, ?, ?, ?, 1, ?)
                                    ''', (user_id, username, first_name, last_name, moscow_time))
                logger.info(f"👑 Добавлен новый администратор: {first_name} (@{username}) ID: {user_id}")

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при назначении администратора {user_id}: {e}")
            return False

    # ==================== КАТЕГОРИИ ====================
    def get_categories(self):
        try:
            self.cursor.execute("SELECT * FROM categories ORDER BY name")
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []

    def get_category_name(self, category_id: int):
        try:
            self.cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
            row = self.cursor.fetchone()
            return row['name'] if row else "Неизвестно"
        except:
            return "Неизвестно"

    # ==================== ТОВАРЫ ====================
    def add_product(self, category: str, name: str, price: int, description: str = "", photo_id: str = None):
        """Добавление товара - ПРОСТОЕ"""
        try:
            self.cursor.execute('''
                INSERT INTO products (category, name, price, description, photo_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (category, name, price, description, photo_id))
            self.conn.commit()
            product_id = self.cursor.lastrowid
            logger.info(f"✅ Товар добавлен: {name} (ID: {product_id})")
            return product_id
        except Exception as e:
            logger.error(f"❌ Ошибка добавления товара: {e}")
            return 0

    def delete_product(self, product_id: int):
        """Простое удаление - ставим is_active = 0"""
        try:
            self.cursor.execute('''
                UPDATE products SET is_active = 0 WHERE id = ?
            ''', (product_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except:
            return False

    def get_product_by_id(self, product_id: int):
        try:
            self.cursor.execute('''
                SELECT * FROM products 
                WHERE id = ? AND is_active = 1
            ''', (product_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except:
            return None

    def get_products_by_category(self, category_name: str):
        try:
            self.cursor.execute('''
                SELECT * FROM products 
                WHERE category = ? AND is_active = 1
                ORDER BY name
            ''', (category_name,))
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []

    def get_all_products(self):
        try:
            self.cursor.execute('''
                SELECT * FROM products 
                WHERE is_active = 1
                ORDER BY category, name
            ''')
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []

    def search_products(self, query: str):
        try:
            self.cursor.execute('''
                SELECT * FROM products 
                WHERE is_active = 1 AND name LIKE ?
                ORDER BY name
            ''', (f"%{query}%",))
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []

    def get_user_count(self):
        """Получить общее количество пользователей"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM users")
            row = self.cursor.fetchone()
            return row['count'] if row else 0
        except:
            return 0

    def get_admin_count(self):
        """Получить количество администраторов"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = 1")
            row = self.cursor.fetchone()
            return row['count'] if row else 0
        except:
            return 0

    def get_all_users(self, limit: int = 100):
        """Получить всех пользователей (для админки)"""
        try:
            self.cursor.execute("SELECT * FROM users ORDER BY join_date DESC LIMIT ?", (limit,))
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []

    def get_user_by_id(self, user_id: int):
        """Получить информацию о пользователе по ID"""
        try:
            self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = self.cursor.fetchone()

            if row:
                user_data = dict(row)
                # Заменяем None на пустые строки для красивого отображения
                for key in ['username', 'first_name', 'last_name']:
                    if user_data.get(key) is None:
                        user_data[key] = 'Не указано'

                # Форматируем дату в московское время
                if 'join_date' in user_data and user_data['join_date']:
                    user_data['join_date'] = self.format_moscow_time(user_data['join_date'])

                return user_data
            return None

        except Exception as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None

    def get_current_moscow_datetime(self):
        """Получить текущую дату и время по Москве"""
        utc_now = datetime.utcnow()
        moscow_time = utc_now + timedelta(hours=3)
        return moscow_time

    def get_current_moscow_time_str(self):
        """Получить текущую дату и время по Москве в виде строки"""
        moscow_time = self.get_current_moscow_datetime()
        return moscow_time.strftime('%d.%m.%Y %H:%M:%S')

    # Категории

    def add_category(self, name: str, emoji: str = "📦") -> int:
        """Добавить новую категорию"""
        try:
            self.cursor.execute('''
                                INSERT
                                OR IGNORE INTO categories (name, emoji)
                VALUES (?, ?)
                                ''', (name, emoji))
            self.conn.commit()

            if self.cursor.rowcount > 0:
                category_id = self.cursor.lastrowid
                logger.info(f"✅ Добавлена категория: {emoji} {name} (ID: {category_id})")
                return category_id
            else:
                logger.warning(f"⚠️ Категория '{name}' уже существует")
                return 0

        except Exception as e:
            logger.error(f"❌ Ошибка добавления категории '{name}': {e}")
            return 0

    def delete_category(self, category_id: int) -> bool:
        """Удалить категорию полностью из БД"""
        try:
            # Сначала проверяем, есть ли товары в этой категории
            self.cursor.execute('''
                                SELECT name
                                FROM categories
                                WHERE id = ?
                                ''', (category_id,))
            category = self.cursor.fetchone()

            if not category:
                logger.warning(f"Категория ID {category_id} не найдена")
                return False

            category_name = category['name']

            # Проверяем, есть ли товары в этой категории
            self.cursor.execute('''
                                SELECT COUNT(*) as count
                                FROM products
                                WHERE category = ?
                                ''', (category_name,))
            result = self.cursor.fetchone()

            if result and result['count'] > 0:
                logger.warning(f"Нельзя удалить категорию {category_id}: есть {result['count']} товаров")
                return False

            # Удаляем категорию (настоящее удаление, а не пометка)
            self.cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            self.conn.commit()

            deleted = self.cursor.rowcount > 0
            if deleted:
                logger.info(f"🗑️ Категория ID: {category_id} удалена из БД")
            else:
                logger.warning(f"Категория ID: {category_id} не была удалена (возможно не найдена)")

            return deleted

        except Exception as e:
            logger.error(f"❌ Ошибка удаления категории {category_id}: {e}")
            return False

    def update_category(self, category_id: int, name: str = None, emoji: str = None) -> bool:
        """Обновить категорию"""
        try:
            updates = []
            params = []

            if name:
                updates.append("name = ?")
                params.append(name)

            if emoji:
                updates.append("emoji = ?")
                params.append(emoji)

            if not updates:
                return False

            params.append(category_id)

            query = f"UPDATE categories SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            self.conn.commit()

            updated = self.cursor.rowcount > 0
            if updated:
                logger.info(f"✏️ Обновлена категория ID: {category_id}")
            return updated

        except Exception as e:
            logger.error(f"❌ Ошибка обновления категории {category_id}: {e}")
            return False

# Глобальный экземпляр
db = Database()