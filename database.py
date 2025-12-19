# database.py - ДОПОЛНЯЕМ МЕТОДЫ ДЛЯ ТОВАРОВ
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name: str = 'vapeshop.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info(f"База данных {db_name} подключена")

    def create_tables(self):
        """Создание всех необходимых таблиц"""
        # Таблица пользователей (уже есть)
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
                                language_code
                                TEXT,
                                is_bot
                                BOOLEAN
                                DEFAULT
                                0,
                                is_admin
                                BOOLEAN
                                DEFAULT
                                0,
                                join_date
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                last_activity
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                notifications_enabled
                                BOOLEAN
                                DEFAULT
                                1
                            )
                            ''')

        # Таблица категорий товаров
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
                                description
                                TEXT,
                                is_active
                                BOOLEAN
                                DEFAULT
                                1,
                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            ''')

        # Таблица товаров (обновленная с photo_id)
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS products
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                category_id
                                INTEGER
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
                                TEXT, -- ID фотографии в Telegram
                                stock
                                INTEGER
                                DEFAULT
                                0,
                                is_active
                                BOOLEAN
                                DEFAULT
                                1,
                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                updated_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP,
                                FOREIGN
                                KEY
                            (
                                category_id
                            ) REFERENCES categories
                            (
                                id
                            )
                                )
                            ''')

        # Добавляем категории по умолчанию
        default_categories = [
            ('POD-системы', 'Одноразовые и многоразовые POD-системы'),
            ('Жидкости', 'Жидкости для заправки'),
            ('Испарители', 'Сменные испарители и атомайзеры'),
            ('Аксессуары', 'Аксессуары для вейпинга'),
            ('Комплектующие', 'Запчасти и комплектующие')
        ]

        for category_name, description in default_categories:
            self.cursor.execute('''
                                INSERT
                                OR IGNORE INTO categories (name, description) 
                VALUES (?, ?)
                                ''', (category_name, description))

        self.conn.commit()
        logger.info("Таблицы созданы/проверены")

    # ==================== МЕТОДЫ ДЛЯ КАТЕГОРИЙ ====================

    def get_categories(self) -> List[Dict]:
        """Получение всех категорий"""
        try:
            self.cursor.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY name")
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []

    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        """Получение категории по ID"""
        try:
            self.cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении категории: {e}")
            return None

    def add_category(self, name: str, description: str = "") -> int:
        """Добавление новой категории"""
        try:
            self.cursor.execute('''
                                INSERT INTO categories (name, description)
                                VALUES (?, ?)
                                ''', (name, description))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении категории: {e}")
            return 0

    # ==================== МЕТОДЫ ДЛЯ ТОВАРОВ ====================

    def add_product(self, category_id: int, name: str, price: int,
                    description: str = "", photo_id: str = None, stock: int = 0) -> int:
        """Добавление нового товара"""
        try:
            self.cursor.execute('''
                                INSERT INTO products
                                    (category_id, name, price, description, photo_id, stock)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ''', (category_id, name, price, description, photo_id, stock))
            self.conn.commit()
            product_id = self.cursor.lastrowid
            logger.info(f"Товар '{name}' добавлен с ID {product_id}")
            return product_id
        except Exception as e:
            logger.error(f"Ошибка при добавлении товара: {e}")
            return 0

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Обновление информации о товаре"""
        try:
            if not kwargs:
                return False

            set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(product_id)

            self.cursor.execute(f'''
                UPDATE products 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', values)
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении товара: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """Удаление товара (мягкое удаление)"""
        try:
            self.cursor.execute('''
                                UPDATE products
                                SET is_active  = 0,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                                ''', (product_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении товара: {e}")
            return False

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Получение товара по ID"""
        try:
            self.cursor.execute('''
                                SELECT p.*, c.name as category_name
                                FROM products p
                                         JOIN categories c ON p.category_id = c.id
                                WHERE p.id = ?
                                  AND p.is_active = 1
                                ''', (product_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении товара: {e}")
            return None

    def get_products_by_category(self, category_id: int) -> List[Dict]:
        """Получение товаров по категории"""
        try:
            self.cursor.execute('''
                                SELECT p.*, c.name as category_name
                                FROM products p
                                         JOIN categories c ON p.category_id = c.id
                                WHERE p.category_id = ?
                                  AND p.is_active = 1
                                ORDER BY p.name
                                ''', (category_id,))
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении товаров: {e}")
            return []

    def get_all_products(self, active_only: bool = True) -> List[Dict]:
        """Получение всех товаров"""
        try:
            query = '''
                    SELECT p.*, c.name as category_name
                    FROM products p
                             JOIN categories c ON p.category_id = c.id \
                    '''
            if active_only:
                query += " WHERE p.is_active = 1"
            query += " ORDER BY p.category_id, p.name"

            self.cursor.execute(query)
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении всех товаров: {e}")
            return []

    def search_products(self, query: str) -> List[Dict]:
        """Поиск товаров по названию"""
        try:
            self.cursor.execute('''
                                SELECT p.*, c.name as category_name
                                FROM products p
                                         JOIN categories c ON p.category_id = c.id
                                WHERE p.is_active = 1
                                  AND p.name LIKE ?
                                ORDER BY p.name
                                ''', (f"%{query}%",))
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при поиске товаров: {e}")
            return []

    def get_products_count(self) -> int:
        """Получение количества товаров"""
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете товаров: {e}")
            return 0

    # ==================== МЕТОДЫ ДЛЯ ФОТОГРАФИЙ ====================

    def save_product_photo(self, product_id: int, photo_id: str) -> bool:
        """Сохранение ID фотографии для товара"""
        try:
            self.cursor.execute('''
                                UPDATE products
                                SET photo_id   = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                                ''', (photo_id, product_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при сохранении фото: {e}")
            return False

    def get_product_with_photo(self, product_id: int) -> Optional[Dict]:
        """Получение товара с фото"""
        try:
            self.cursor.execute('''
                                SELECT p.*, c.name as category_name
                                FROM products p
                                         JOIN categories c ON p.category_id = c.id
                                WHERE p.id = ?
                                  AND p.is_active = 1
                                  AND p.photo_id IS NOT NULL
                                ''', (product_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении товара с фото: {e}")
            return None


# Создаем глобальный экземпляр базы данных
db = Database()