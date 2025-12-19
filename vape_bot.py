# CloudBot
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import TOKEN
import admin
import category_manager
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== ПОЛЬЗОВАТЕЛЬСКИЙ ИНТЕРФЕЙС ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    user = update.effective_user

    # Сохранение пользователя со всеми данными
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    welcome_text = (
        f"Привет, {user.first_name}!\n"
        "Добро пожаловать в CloudVape Shop! 🛒\n\n"
        "Выберите категорию товаров:"
    )

    # Получаем категории
    categories = db.get_categories()

    keyboard = []
    for category in categories:
        # Используем ID категории для callback_data
        keyboard.append([
            InlineKeyboardButton(
                f"{category['emoji']} {category['name']}",
                callback_data=f'cat_{category["id"]}'
            )
        ])

    keyboard.append([InlineKeyboardButton("📞 Контакты", callback_data='contacts')])
    keyboard.append([InlineKeyboardButton("ℹ️ Помощь", callback_data='help')])

    if db.is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Админка", callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать товары категории - ЗАЩИЩЕННАЯ ВЕРСИЯ"""
    query = update.callback_query
    await query.answer()

    try:
        # Безопасное получение ID категории
        callback_data = query.data

        # Проверяем что это действительно cat_число
        if not callback_data.startswith('cat_'):
            return

        category_id_str = callback_data.replace('cat_', '')

        # Проверяем что это число
        if not category_id_str.isdigit():
            logger.warning(f"Некорректный callback_data: {callback_data}")
            return

        category_id = int(category_id_str)

        # Получаем категорию
        categories = db.get_categories()
        category = next((c for c in categories if c['id'] == category_id), None)

        if not category:
            await query.edit_message_text("❌ Категория не найдена")
            return

        # Получаем товары этой категории
        products = db.get_products_by_category(category['name'])

        text = f"<b>{category['emoji']} {category['name']}</b>\n\n"

        if not products:
            text += "📦 Товаров пока нет"
            keyboard = []
        else:
            text += "Выберите товар:\n"
            keyboard = []
            for product in products:
                btn_text = f"{product['name']} - {product['price']}₽"
                keyboard.append([
                    InlineKeyboardButton(btn_text, callback_data=f'prod_{product["id"]}')
                ])

        # Кнопка назад
        keyboard.append([InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Ошибка в show_category: {e}")
        await query.edit_message_text("❌ Произошла ошибка при загрузке категории")


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать товар"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace('prod_', ''))
    product = db.get_product_by_id(product_id)

    if not product:
        await query.edit_message_text("❌ Товар не найден")
        return

    # Получаем категорию для кнопки назад
    categories = db.get_categories()
    category = next((c for c in categories if c['name'] == product['category']), None)

    text = (
        f"<b>{product['name']}</b>\n\n"
        f"💰 <b>Цена: {product['price']}₽</b>\n"
        f"📦 Категория: {product['category']}\n"
        f"📝 {product.get('description', 'Нет описания')}\n\n"
        "📞 Для заказа:\n"
        "• Напишите @CloudVape_152\n"
    )

    # Создаем кнопки
    keyboard = []

    if category:
        keyboard.append([
            InlineKeyboardButton(
                f"⬅️ Назад в {category['emoji']} {category['name']}",
                callback_data=f'cat_{category["id"]}'
            )
        ])

    keyboard.append([InlineKeyboardButton("🛒 В главное меню", callback_data='back_to_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # для фото отправляем новое сообщение и сохраняем его message_id
    if product.get('photo_id'):
        # Отправляем новое фото с кнопками
        sent_message = await query.message.reply_photo(
            photo=product['photo_id'],
            caption=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        # Сохраняем message_id в контексте, чтобы потом можно было удалить
        context.user_data['last_photo_message_id'] = sent_message.message_id
        context.user_data['last_photo_chat_id'] = sent_message.chat_id

        # Не удаляем старое сообщение, чтобы пользователь мог вернуться
        # Просто ничего не делаем со старым сообщением
    else:
        # Без фото - редактируем текущее сообщение
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def cleanup_old_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить старые фото-сообщения при возврате в меню"""
    chat_id = update.callback_query.message.chat_id

    # Пытаемся удалить предыдущее фото-сообщение
    last_photo_id = context.user_data.get('last_photo_message_id')
    last_chat_id = context.user_data.get('last_photo_chat_id')

    if last_photo_id and last_chat_id == chat_id:
        try:
            await context.bot.delete_message(
                chat_id=last_chat_id,
                message_id=last_photo_id
            )
            # Очищаем из контекста
            context.user_data.pop('last_photo_message_id', None)
            context.user_data.pop('last_photo_chat_id', None)
        except Exception as e:
            logger.info(f"Не удалось удалить старое фото: {e}")


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню с очисткой старых фото"""
    query = update.callback_query
    await query.answer()

    # Очищаем старые фото
    await cleanup_old_photos(update, context)

    text = "🛒 <b>Главное меню</b>\n\nВыберите категорию:"

    categories = db.get_categories()
    keyboard = []
    for category in categories:
        keyboard.append([
            InlineKeyboardButton(
                f"{category['emoji']} {category['name']}",
                callback_data=f'cat_{category["id"]}'
            )
        ])

    keyboard.append([InlineKeyboardButton("📞 Контакты", callback_data='contacts')])
    keyboard.append([InlineKeyboardButton("ℹ️ Помощь", callback_data='help')])

    if db.is_admin(query.from_user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Админка", callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Редактируем текущее сообщение (или отправляем новое, если было удалено)
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except:
        # Если сообщение было удалено, отправляем новое
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )


async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты"""
    query = update.callback_query
    await query.answer()

    text = (
        "<b>📞 Контакты</b>\n\n"
        "🏪 CloudVape\n"
        "✈️ @CloudVape_152\n\n"
        "🕒 Часы работы:\n"
        "Пн-Пт: 10:00 - 22:00\n"
        "Сб-Вс: 11:00 - 23:00"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    query = update.callback_query
    await query.answer()

    text = (
        "<b>ℹ️ Помощь</b>\n\n"
        "1. Выберите категорию товаров\n"
        "2. Выберите товар\n"
        "3. Напишите нам для заказа\n\n"
        "📞 Контакты есть в соответствующем разделе"
    )

    keyboard = [
        [InlineKeyboardButton("📞 Контакты", callback_data='contacts')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


# ==================== АДМИН КОМАНДЫ ====================

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора - команда /admin"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    # НОВОЕ: получаем реальную статистику
    user_count = db.get_user_count()  # Используем новую функцию!
    admin_count = db.get_admin_count()
    products = db.get_all_products()
    product_count = len(products)

    text = (
        f"⚙️ <b>Панель администратора VapeShop</b>\n\n"
        f"📊 <b>Статистика магазина:</b>\n"
        f"• 👥 Пользователей: {user_count}\n"
        f"• 👑 Администраторов: {admin_count}\n"
        f"• 📦 Товаров: {product_count}\n\n"
        "<b>🏷️ Управление категориями:</b>\n"
        "<code>/categories</code> - Все категории\n"
        "<code>/add_category</code> - Добавить категорию\n"
        "<code>/delete_category</code> - Удалить категорию\n\n"
        "<b>📦 Управление товарами:</b>\n"
        "<code>/add_product</code> - Добавить товар\n"
        "<code>/delete_product [ID]</code> - Удалить товар\n"
        "<code>/list_products</code> - Список всех товаров\n"
        "<code>/search_product [текст]</code> - Поиск товара\n\n"
        "<b>📢 Рассылка:</b>\n"
        "<code>/broadcast [текст]</code> - Рассылка сообщения\n\n"
        "<b>👥 Управление пользователями:</b>\n"
        "<code>/user_info [ID]</code> - Информация о пользователе\n"
        "<code>/list_admins</code> - Список админов\n"
        "<code>/make_admin [ID]</code> - Назначить админом\n\n"
        "<b>📊 Статистика:</b>\n"
        "<code>/stats</code> - Подробная статистика\n\n"
        "<i>Просто введите команду в чат</i>"
    )

    keyboard = [[InlineKeyboardButton("⬅️ В главное меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')


# ==================== ЗАПУСК БОТА ====================

def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Добавляем админа
    db.add_admin(907331808)

    # ==================== ОСНОВНЫЕ КОМАНДЫ ====================
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_commands))

    # ==================== ОБРАБОТЧИКИ КНОПОК ====================
    application.add_handler(CallbackQueryHandler(show_category, pattern='^cat_\d+$'))
    application.add_handler(CallbackQueryHandler(show_product, pattern='^prod_'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$'))
    application.add_handler(CallbackQueryHandler(show_contacts, pattern='^contacts$'))
    application.add_handler(CallbackQueryHandler(show_help, pattern='^help$'))
    application.add_handler(CallbackQueryHandler(admin.admin_panel_handler, pattern='^admin_panel$'))

    # ==================== УПРАВЛЕНИЕ ТОВАРАМИ ====================
    from product_manager import add_product_conversation
    application.add_handler(add_product_conversation)
    application.add_handler(
        CallbackQueryHandler(admin.delete_callback_handler, pattern='^del_|confirm_delete|cancel_delete|del_cancel$'))
    application.add_handler(CommandHandler("delete_product", admin.delete_product_command))
    application.add_handler(CommandHandler("list_products", admin.list_products_command))
    application.add_handler(CommandHandler("search_product", admin.search_product_command))

    # ==================== УПРАВЛЕНИЕ КАТЕГОРИЯМИ ====================
    from category_manager import (
        add_category_conversation,
        delete_category_conversation,
        categories_command
        # list_categories_command больше нет
    )

    # Простые команды
    application.add_handler(CommandHandler("categories", categories_command))

    # ConversationHandler для добавления категории
    application.add_handler(add_category_conversation)

    # ConversationHandler для удаления категории
    application.add_handler(delete_category_conversation)

    # ==================== ДРУГИЕ АДМИН КОМАНДЫ ====================
    application.add_handler(CommandHandler("stats", admin.stats_command))
    application.add_handler(CommandHandler("broadcast", admin.broadcast_command))
    application.add_handler(CommandHandler("user_info", admin.user_info_command))
    application.add_handler(CommandHandler("make_admin", admin.make_admin_command))

    print("=" * 50)
    print("🤖 Бот запущен!")
    print("=" * 50)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()