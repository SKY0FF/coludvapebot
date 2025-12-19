# vape_bot.py - ОБНОВЛЕННЫЙ
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import TOKEN
import admin
from database import db
import product_manager  # Импортируем новый модуль

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# ==================== ОБНОВЛЯЕМ ФУНКЦИИ ДЛЯ РАБОТЫ С БД ====================

# Заменяем статический словарь PRODUCTS на загрузку из БД
async def get_products_from_db():
    """Загрузка товаров из базы данных"""
    products = {}

    categories = db.get_categories()
    for category in categories:
        category_key = category['name'].lower().replace('-', '').replace(' ', '_')
        category_items = db.get_products_by_category(category['id'])

        items_list = []
        for item in category_items:
            items_list.append({
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'description': item.get('description', ''),
                'photo_id': item.get('photo_id')
            })

        products[category_key] = {
            'name': category['name'],
            'items': items_list
        }

    return products


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать товары в категории (обновленная версия)"""
    query = update.callback_query
    await query.answer()

    category_id = query.data.replace('category_', '')

    # Загружаем категории из БД
    categories = db.get_categories()

    # Находим нужную категорию
    category = None
    for cat in categories:
        cat_key = cat['name'].lower().replace('-', '').replace(' ', '_')
        if cat_key == category_id:
            category = cat
            break

    if not category:
        await query.edit_message_text("❌ Категория не найдена.")
        return

    # Получаем товары из БД
    products = db.get_products_by_category(category['id'])

    if not products:
        text = f"<b>{category['name']}</b>\n\n📦 В этой категории пока нет товаров."
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_categories')]]
    else:
        text = f"<b>{category['name']}</b>\n\n"

        # Создаем кнопки для товаров
        keyboard = []
        for item in products:
            item_text = f"{item['name']} - {item['price']}₽"
            keyboard.append([InlineKeyboardButton(item_text, callback_data=f'item_{item["id"]}')])

    # Кнопка назад
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_categories')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')


async def show_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о товаре (обновленная версия)"""
    query = update.callback_query
    await query.answer()

    item_id = int(query.data.replace('item_', ''))

    # Получаем товар из БД
    item = db.get_product_by_id(item_id)

    if not item:
        await query.edit_message_text("❌ Товар не найден.")
        return

    text = (
        f"<b>{item['name']}</b>\n"
        f"💰 Цена: <b>{item['price']}₽</b>\n"
        f"📝 Описание: {item.get('description', 'Нет описания')}\n"
        f"📦 Категория: {item['category_name']}\n\n"
        "Чтобы заказать, напишите нам в WhatsApp или Telegram\n"
        "или позвоните по номеру из раздела 'Контакты'"
    )

    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к категории",
                              callback_data=f'category_{item["category_name"].lower().replace("-", "").replace(" ", "_")}')],
        [InlineKeyboardButton("🛒 Вернуться в каталог", callback_data='back_to_categories')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Если есть фото, отправляем его
    if item.get('photo_id'):
        await query.message.reply_photo(
            photo=item['photo_id'],
            caption=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        await query.delete_message()
    else:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')


async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к списку категорий (обновленная версия)"""
    query = update.callback_query
    await query.answer()

    # Загружаем категории из БД
    categories = db.get_categories()

    text = "🛒 <b>Выберите категорию товаров:</b>"

    keyboard = []
    for category in categories:
        category_key = category['name'].lower().replace('-', '').replace(' ', '_')
        keyboard.append([
            InlineKeyboardButton(category['name'], callback_data=f'category_{category_key}')
        ])

    keyboard.append([InlineKeyboardButton("📞 Контакты", callback_data='contacts')])
    keyboard.append([InlineKeyboardButton("ℹ️ Помощь", callback_data='help')])

    # Проверяем, является ли пользователь администратором
    user_id = query.from_user.id
    if db.is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')


# ... остальные функции (start, show_all_products, show_prices и т.д.) остаются без изменений ...

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

    # Обработчики для управления товарами (только для админов)
    application.add_handler(product_manager.add_product_conversation)  # Добавление товара
    application.add_handler(CommandHandler("delete_product", product_manager.delete_product_command))
    application.add_handler(CommandHandler("list_products", product_manager.list_products_command))
    application.add_handler(CommandHandler("search_product", product_manager.search_product_command))

    # Обработчики для удаления товаров через callback
    application.add_handler(CallbackQueryHandler(
        product_manager.confirm_delete, pattern='^(del_prod_|cancel_delete)'
    ))
    application.add_handler(CallbackQueryHandler(
        product_manager.execute_delete, pattern='^delete_confirm_'
    ))

    # Обработчики административных команд
    application.add_handler(CommandHandler("admin", admin.admin_panel))
    application.add_handler(CommandHandler("stats", admin.show_stats))
    application.add_handler(CommandHandler("broadcast", admin.broadcast_command))
    application.add_handler(CommandHandler("broadcast_history", admin.broadcast_history))
    application.add_handler(CommandHandler("make_admin", admin.make_admin))
    application.add_handler(CommandHandler("user_info", admin.user_info))

    # Обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(show_category, pattern='^category_'))
    application.add_handler(CallbackQueryHandler(show_item, pattern='^item_'))
    application.add_handler(CallbackQueryHandler(back_to_categories, pattern='^back_to_categories$'))
    application.add_handler(CallbackQueryHandler(show_contacts, pattern='^contacts$'))
    application.add_handler(CallbackQueryHandler(show_help, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(admin.admin_callback_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(admin.confirm_broadcast_callback,
                                                 pattern='^(confirm_broadcast|edit_broadcast|cancel_broadcast)'))

    # Запускаем бота
    print("=" * 50)
    print("🤖 Бот запущен!")
    print(f"📊 База данных: {db.db_name}")
    print(f"👑 Администраторы: {admin.DEFAULT_ADMINS}")
    print("=" * 50)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()