# check_admins.py
from database import db

print("=" * 60)
print("ПРОВЕРКА АДМИНИСТРАТОРОВ В БАЗЕ ДАННЫХ")
print("=" * 60)

# Прямой SQL запрос
db.cursor.execute("SELECT * FROM users WHERE is_admin = 1")
admins = db.cursor.fetchall()

print(f"Всего администраторов: {len(admins)}\n")

for admin in admins:
    print(f"ID: {admin['user_id']}")
    print(f"  Имя: {admin['first_name']}")
    print(f"  Фамилия: {admin['last_name']}")
    print(f"  Username: {admin['username']}")
    print(f"  Дата регистрации: {admin['join_date']}")
    print(f"  Главный: {'Да' if admin['user_id'] == 907331808 else 'Нет'}")
    print()