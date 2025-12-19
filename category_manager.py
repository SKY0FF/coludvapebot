# category_manager.py - ЗАМЕНИТЕ НА ЭТОТ КОД (убрана list_categories_command):

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    MessageHandler, filters
)
from database import db
import logging

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
ADD_NAME, ADD_EMOJI, CONFIRM_ADD, DELETE_CONFIRM = range(4)


# ==================== КОМАНДА ДЛЯ УПРАВЛЕНИЯ КАТЕГОРИЯМИ ====================

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главная команда для управления категориями - показывает список и команды"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    categories = db.get_categories()

    text = "🏷️ <b>Управление категориями товаров</b>\n\n"

    if not categories:
        text += "📭 Нет категорий\n\n"
    else:
        text += "<b>Текущие категории:</b>\n"
        for i, category in enumerate(categories, 1):
            # Считаем товары в категории
            products = db.get_products_by_category(category['name'])
            count = len(products)

            text += f"{i}. {category['emoji']} <b>{category['name']}</b>\n"
            text += f"   Товаров: {count}\n"
            text += f"   ID: <code>{category['id']}</code>\n\n"

    text += "<b>Доступные команды:</b>\n"
    text += "<code>/add_category</code> - Добавить новую категорию\n"
    text += "<code>/delete_category [ID]</code> - Удалить категорию\n\n"
    text += "<i>Пример: /delete_category 1</i>"

    await update.message.reply_text(text, parse_mode='HTML')


# ==================== ДОБАВЛЕНИЕ КАТЕГОРИИ ====================

async def add_category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add_category - запуск добавления категории"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return ConversationHandler.END

    await update.message.reply_text(
        "🏷️ <b>Добавление новой категории</b>\n\n"
        "Введите название категории:\n\n"
        "<i>Пример: Одноразовые электронные сигареты</i>\n\n"
        "Или /cancel для отмены",
        parse_mode='HTML'
    )

    return ADD_NAME


async def add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия категории"""
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text("❌ Название не может быть пустым. Введите название:")
        return ADD_NAME

    if len(name) > 50:
        await update.message.reply_text("❌ Название слишком длинное (макс. 50 символов). Введите снова:")
        return ADD_NAME

    context.user_data['new_category'] = {'name': name}

    await update.message.reply_text(
        f"✅ Название: <b>{name}</b>\n\n"
        "Введите эмодзи для категории:\n\n"
        "<i>Пример: 🚬 или 🔋 или 💨</i>\n"
        "Или отправьте /skip для эмодзи по умолчанию (📦)\n\n"
        "Или /cancel для отмены",
        parse_mode='HTML'
    )

    return ADD_EMOJI


async def add_category_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод эмодзи категории"""
    emoji = update.message.text.strip()

    # Проверяем что это эмодзи (примерно)
    if len(emoji) > 2:  # Эмодзи обычно 1-2 символа
        await update.message.reply_text(
            "❌ Похоже, это не эмодзи. Введите один эмодзи:\n"
            "<i>Пример: 🔋, 💨, 🚬, ⚡, 💧</i>\n\n"
            "Или /skip для эмодзи по умолчанию (📦)\n"
            "Или /cancel для отмены",
            parse_mode='HTML'
        )
        return ADD_EMOJI

    context.user_data['new_category']['emoji'] = emoji

    await confirm_add_category(update, context)
    return CONFIRM_ADD


async def skip_category_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск ввода эмодзи"""
    context.user_data['new_category']['emoji'] = "📦"

    await confirm_add_category(update, context)
    return CONFIRM_ADD


async def confirm_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение добавления категории"""
    category_data = context.user_data['new_category']

    text = (
        f"🏷️ <b>Новая категория:</b>\n\n"
        f"{category_data['emoji']} <b>{category_data['name']}</b>\n\n"
        "Добавить эту категорию? Отправьте:\n"
        "<code>да</code> - чтобы добавить\n"
        "<code>нет</code> - чтобы отменить\n\n"
        "Или команду /cancel"
    )

    await update.message.reply_text(text, parse_mode='HTML')
    return CONFIRM_ADD


async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение категории в БД"""
    user_input = update.message.text.strip().lower()

    if user_input == 'да':
        category_data = context.user_data['new_category']

        # Добавляем категорию в БД
        category_id = db.add_category(
            name=category_data['name'],
            emoji=category_data['emoji']
        )

        if category_id > 0:
            await update.message.reply_text(
                f"✅ <b>Категория успешно добавлена!</b>\n\n"
                f"{category_data['emoji']} <b>{category_data['name']}</b>\n"
                f"ID категории: <code>{category_id}</code>\n\n"
                f"Добавить товар в эту категорию: /add_product\n"
                f"Вернуться в управление категориями: /categories",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Не удалось добавить категорию!</b>\n\n"
                f"Возможно, категория с названием '{category_data['name']}' уже существует.",
                parse_mode='HTML'
            )

        context.user_data.clear()
        return ConversationHandler.END

    elif user_input == 'нет':
        await update.message.reply_text("❌ Добавление категории отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "❌ Не понял команду. Отправьте:\n"
            "<code>да</code> - чтобы добавить\n"
            "<code>нет</code> - чтобы отменить\n\n"
            "Или команду /cancel"
        )
        return CONFIRM_ADD


# ==================== УДАЛЕНИЕ КАТЕГОРИИ ====================

async def delete_category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete_category - удаление категории по ID"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    if not context.args:
        # Показываем список категорий для удаления
        categories = db.get_categories()

        if not categories:
            await update.message.reply_text("📭 Нет категорий для удаления.")
            return

        text = "🗑️ <b>Удаление категории</b>\n\n"
        text += "<b>Доступные категории:</b>\n"

        for category in categories:
            products = db.get_products_by_category(category['name'])
            count = len(products)

            text += f"{category['emoji']} <b>{category['name']}</b>\n"
            text += f"   Товаров: {count}\n"
            text += f"   ID: <code>{category['id']}</code>\n\n"

        text += "<b>Использование:</b>\n"
        text += "<code>/delete_category [ID_категории]</code>\n\n"
        text += "<i>Пример: /delete_category 1</i>"

        await update.message.reply_text(text, parse_mode='HTML')
        return

    # Если передан ID категории
    try:
        category_id = int(context.args[0])

        # Получаем информацию о категории
        categories = db.get_categories()
        category = next((c for c in categories if c['id'] == category_id), None)

        if not category:
            await update.message.reply_text(f"❌ Категория с ID {category_id} не найдена.")
            return

        # Считаем товары в категории
        products = db.get_products_by_category(category['name'])
        count = len(products)

        if count > 0:
            await update.message.reply_text(
                f"❌ <b>Нельзя удалить категорию!</b>\n\n"
                f"{category['emoji']} <b>{category['name']}</b>\n"
                f"ID: {category_id}\n\n"
                f"⚠️ В этой категории есть <b>{count} товаров</b>!\n\n"
                f"Сначала удалите или переместите товары:\n"
                f"/delete_product - удалить товары\n"
                f"/list_products - список товаров",
                parse_mode='HTML'
            )
            return

        # Сохраняем ID для подтверждения
        context.user_data['delete_category_id'] = category_id

        await update.message.reply_text(
            f"🗑️ <b>Подтвердите удаление категории</b>\n\n"
            f"{category['emoji']} <b>{category['name']}</b>\n"
            f"ID: {category_id}\n\n"
            "Отправьте:\n"
            "<code>да</code> - чтобы удалить\n"
            "<code>нет</code> - чтобы отменить",
            parse_mode='HTML'
        )

        return DELETE_CONFIRM

    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Используйте: /delete_category [ID_категории]")


async def confirm_delete_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления категории"""
    user_input = update.message.text.strip().lower()

    if user_input == 'да':
        category_id = context.user_data.get('delete_category_id')

        if not category_id:
            await update.message.reply_text("❌ Ошибка: ID категории не найден.")
            context.user_data.clear()
            return ConversationHandler.END

        # Удаляем категорию
        success = db.delete_category(category_id)

        if success:
            await update.message.reply_text(
                f"✅ <b>Категория успешно удалена!</b>\n\n"
                f"ID категории: {category_id}\n\n"
                f"Вернуться в управление категориями: /categories",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Не удалось удалить категорию!</b>\n\n"
                f"ID: {category_id}",
                parse_mode='HTML'
            )

        context.user_data.clear()
        return ConversationHandler.END

    elif user_input == 'нет':
        await update.message.reply_text("❌ Удаление категории отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "❌ Не понял команду. Отправьте:\n"
            "<code>да</code> - чтобы удалить\n"
            "<code>нет</code> - чтобы отменить"
        )
        return DELETE_CONFIRM


async def cancel_category_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена управления категориями"""
    await update.message.reply_text("❌ Управление категориями отменено.")
    context.user_data.clear()
    return ConversationHandler.END


# ==================== ConversationHandler для добавления категории ====================

add_category_conversation = ConversationHandler(
    entry_points=[CommandHandler('add_category', add_category_command)],
    states={
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_name)],
        ADD_EMOJI: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_emoji),
            CommandHandler('skip', skip_category_emoji),
        ],
        CONFIRM_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_category)],
    },
    fallbacks=[CommandHandler('cancel', cancel_category_management)],
    per_message=False,
)

# ==================== ConversationHandler для удаления категории ====================

delete_category_conversation = ConversationHandler(
    entry_points=[CommandHandler('delete_category', delete_category_command)],
    states={
        DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_category)],
    },
    fallbacks=[CommandHandler('cancel', cancel_category_management)],
    per_message=False,
)