# vape_bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import TOKEN
import admin
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Каталог товаров
PRODUCTS = {
    'pod_systems': {
        'name': 'POD-системы',
        'items': [
            {'id': 1, 'name': 'HQD Cuvie Plus', 'price': 899, 'description': '800 тяг, 12 вкусов'},
            {'id': 2, 'name': 'Elf Bar BC5000', 'price': 1299, 'description': '5000 тяг, 15 вкусов'},
            {'id': 3, 'name': 'VOOPOO Drag S', 'price': 3499, 'description': 'Сменные картриджи, 60W'},
            {'id': 4, 'name': 'Uwell Caliburn G2', 'price': 2899, 'description': 'Регулируемая тяга, 18W'},
        ]
    },
    'liquids': {
        'name': 'Жидкости',
        'items': [
            {'id': 5, 'name': 'Jam Monster 100ml', 'price': 1599, 'description': 'Табак с печеньем, 3mg'},
            {'id': 6, 'name': 'Nasty Juice 60ml', 'price': 1199, 'description': 'Фруктовые вкусы, 6mg'},
            {'id': 7, 'name': 'Halo Tribeca 30ml', 'price': 899, 'description': 'Классический табак, 12mg'},
        ]
    },
    'coils': {
        'name': 'Испарители',
        'items': [
            {'id': 8, 'name': 'VOOPOO PnP Coil (0.15Ω)', 'price': 399, 'description': '5 шт в упаковке'},
            {'id': 9, 'name': 'Uwell Caliburn G Coil', 'price': 349, 'description': '4 шт в упаковке'},
            {'id': 10, 'name': 'SMOK TFV9 Coil (0.15Ω)', 'price': 449, 'description': '3 шт в упаковке'},
        ]
    },
    'accessories': {
        'name': 'Аксессуары',
        'items': [
            {'id': 11, 'name': 'Зарядное устройство', 'price': 599, 'description': 'Универсальное, 2A'},
            {'id': 12, 'name': 'Чехол для устройства', 'price': 299, 'description': 'Силиконовый, разные цвета'},
            {'id': 13, 'name': 'Набор для чистки', 'price': 499, 'description': 'Щетки, салфетки, палочки'},
        ]
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с сохранением пользователя"""
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    user_data = {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'is_bot': user.is_bot
    }
    db.add_or_update_user(user_data)
    
    # Проверяем, является ли администратором
    is_admin = db.is_admin(user.id)
    
    welcome_text = (
        f"Привет, {user.first_name}!\n"
        "Добро пожаловать в VapeShop Bot!\n\n"
        "🛒 Выберите категорию товаров:"
    )
    
    # Если администратор - показываем кнопку админки
    keyboard = [
        [InlineKeyboardButton("🔋 POD-системы", callback_data='category_pod_systems')],
        [InlineKeyboardButton("💧 Жидкости", callback_data='category_liquids')],
        [InlineKeyboardButton("⚡ Испарители", callback_data='category_coils')],
        [InlineKeyboardButton("🎒 Аксессуары", callback_data='category_accessories')],
        [InlineKeyboardButton("📞 Контакты", callback_data='contacts')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')],
    ]
    
    if is_admin:
        keyboard.insert(0, [InlineKeyboardButton("⚙️ Админ-панель", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать товары в категории"""
    query = update.callback_query
    await query.answer()
    
    category_id = query.data.replace('category_', '')
    category = PRODUCTS[category_id]
    
    text = f"<b>{category['name']}</b>\n\n"
    
    # Создаем кнопки для товаров
    keyboard = []
    for item in category['items']:
        item_text = f"{item['name']} - {item['price']}₽"
        keyboard.append([InlineKeyboardButton(item_text, callback_data=f'item_{item["id"]}')])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_categories')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')

async def show_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о товаре"""
    query = update.callback_query
    await query.answer()
    
    item_id = int(query.data.replace('item_', ''))
    
    # Ищем товар по ID
    item = None
    category_id = None
    for cat_id, cat_data in PRODUCTS.items():
        for it in cat_data['items']:
            if it['id'] == item_id:
                item = it
                category_id = cat_id
                break
    
    if item:
        text = (
            f"<b>{item['name']}</b>\n"
            f"💰 Цена: <b>{item['price']}₽</b>\n"
            f"📝 Описание: {item['description']}\n\n"
            "Чтобы заказать, напишите нам в WhatsApp или Telegram\n"
            "или позвоните по номеру из раздела 'Контакты'"
        )
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к категории", callback_data=f'category_{category_id}')],
            [InlineKeyboardButton("🛒 Вернуться в каталог", callback_data='back_to_categories')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')

async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к списку категорий"""
    query = update.callback_query
    await query.answer()
    
    text = "🛒 Выберите категорию товаров:"
    
    keyboard = [
        [InlineKeyboardButton("🔋 POD-системы", callback_data='category_pod_systems')],
        [InlineKeyboardButton("💧 Жидкости", callback_data='category_liquids')],
        [InlineKeyboardButton("⚡ Испарители", callback_data='category_coils')],
        [InlineKeyboardButton("🎒 Аксессуары", callback_data='category_accessories')],
        [InlineKeyboardButton("📞 Контакты", callback_data='contacts')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup)

async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать контактную информацию"""
    query = update.callback_query
    await query.answer()
    
    contacts_text = (
        "<b>📞 Контактная информация</b>\n\n"
        "🏪 Магазин: CloudVape\n"
        "✈️ Telegram: @CloudVape_152\n"
        "🕒 Часы работы:\n"
        "Пн-Пт: 10:00 - 22:00\n"
        "Сб-Вс: 12:00 - 22:00"
    )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_categories')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=contacts_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "<b>ℹ️ Помощь</b>\n\n"
        "Этот бот поможет вам ознакомиться с ассортиментом нашего вейп-шопа.\n\n"
        "<b>Как сделать заказ:</b>\n"
        "1. Выберите интересующий товар\n"
        "2. Свяжитесь с нами по контактам из раздела 'Контакты'\n"
        "3. Укажите название товара и его артикул\n\n"
        "<b>Доставка:</b>\n"
        "• Самовывоз из магазина\n"
        "• Курьерская доставка по городу\n"
        "• Доставка по России\n\n"
        "Для связи с менеджером используйте контакты из соответствующего раздела."
    )
    
    keyboard = [
        [InlineKeyboardButton("📞 Контакты", callback_data='contacts')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_categories')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=help_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_all_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все товары (команда /products)"""
    text = "<b>📋 Полный каталог товаров</b>\n\n"
    total_items = 0
    
    for category_id, category_data in PRODUCTS.items():
        text += f"<b>{category_data['name']}:</b>\n"
        for item in category_data['items']:
            text += f"• {item['name']} - {item['price']}₽\n"
        text += "\n"
        total_items += len(category_data['items'])
    
    text += f"<i>Всего товаров: {total_items}</i>"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать цены (команда /prices)"""
    text = "<b>💰 Наши цены</b>\n\n"
    
    # Собираем все товары в один список для сортировки
    all_items = []
    for category_data in PRODUCTS.values():
        all_items.extend(category_data['items'])
    
    # Сортируем по цене
    sorted_items = sorted(all_items, key=lambda x: x['price'])
    
    for item in sorted_items:
        text += f"• {item['name']}: <b>{item['price']}₽</b>\n"
    
    text += "\n<i>Цены могут меняться, актуальные уточняйте у менеджера</i>"
    
    await update.message.reply_text(text, parse_mode='HTML')

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем администраторов по умолчанию
    for admin_id in admin.DEFAULT_ADMINS:
        db.add_admin(admin_id)
    
    # Обработчики команд пользователя
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("products", show_all_products))
    application.add_handler(CommandHandler("prices", show_prices))
    
    # Обработчики административных команд
    application.add_handler(CommandHandler("admin", admin.admin_panel))
    application.add_handler(CommandHandler("stats", admin.show_stats))
    application.add_handler(CommandHandler("broadcast", admin.broadcast_command))
    application.add_handler(CommandHandler("broadcast_history", admin.broadcast_history))
    application.add_handler(CommandHandler("make_admin", admin.make_admin))
    application.add_handler(CommandHandler("user_info", admin.user_info))
    
    # Добавляем ConversationHandler для добавления товара
    application.add_handler(admin.add_product_handler)
    
    # Обработчик редактирования рассылки
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        admin.handle_broadcast_edit
    ))
    
    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(show_category, pattern='^category_'))
    application.add_handler(CallbackQueryHandler(show_item, pattern='^item_'))
    application.add_handler(CallbackQueryHandler(back_to_categories, pattern='^back_to_categories$'))
    application.add_handler(CallbackQueryHandler(show_contacts, pattern='^contacts$'))
    application.add_handler(CallbackQueryHandler(show_help, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(admin.admin_callback_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(admin.confirm_broadcast_callback, pattern='^(confirm_broadcast|edit_broadcast|cancel_broadcast)'))
    
    # Запускаем бота
    print("Бот запущен...")
    print(f"Администраторы по умолчанию: {admin.DEFAULT_ADMINS}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
