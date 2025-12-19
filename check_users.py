# check_users.py
from database import db

print("=" * 60)
print("ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ В БАЗЕ ДАННЫХ")
print("=" * 60)

# Прямой запрос к таблице users
db.cursor.execute("SELECT * FROM users")
rows = db.cursor.fetchall()

print(f"Всего пользователей в базе: {len(rows)}\n")

for i, row in enumerate(rows, 1):
    print(f"{i}. ID: {row['user_id']}")
    print(f"   Имя: {row['first_name'] or 'None'}")
    print(f"   Фамилия: {row['last_name'] or 'None'}")
    print(f"   Username: {row['username'] or 'None'}")
    print(f"   Админ: {'Да' if row['is_admin'] else 'Нет'}")
    print(f"   Дата регистрации: {row['join_date']}")
    print()

# Проверка своей записи
your_id = 907331808  # Ваш ID
db.cursor.execute("SELECT * FROM users WHERE user_id = ?", (your_id,))
your_data = db.cursor.fetchone()

if your_data:
    print(f"\nВаша запись в базе:")
    print(f"ID: {your_data['user_id']}")
    print(f"Имя: {your_data['first_name']}")
    print(f"Фамилия: {your_data['last_name']}")
    print(f"Username: {your_data['username']}")
else:
    print(f"\n❌ Вы не найдены в базе! ID: {your_id}")