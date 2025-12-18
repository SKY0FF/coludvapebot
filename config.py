# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Токен вашего бота
TOKEN = os.getenv("BOT_TOKEN", "8190463518:AAHvdT-XL3v18pVa5ZiJeU0XieIoOPHSn_s")

# Настройки базы данных
DATABASE = {
    'name': 'vapeshop.db',
    'path': './'
}

# Настройки рассылки
BROADCAST = {
    'delay_between_messages': 0.1,  # Задержка между сообщениями (секунды)
    'max_retries': 3,  # Максимальное количество попыток отправки
}
