# product_manager.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)
from database import db
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CATEGORY, NAME, PRICE, DESCRIPTION, PHOTO, CONFIRM, EDIT_CHOICE = range(7)

# Глобальные переменные для временного хранения данных
temp_products = {}


async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления товара"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return ConversationHandler.END

    # Инициализируем временные данные
    context.user_data['new_product'] = {}

    # Получаем список категорий
    categories = db.get_categories()

    if not categories:
        await update.message.reply_text("❌ Нет доступных категорий. Сначала добавьте категории.")
        return ConversationHandler.END

    # Создаем клавиатуру с категориями
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(
            category['name'],
            callback_data=f"add_cat_{category['id']}"
        )])

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_add")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📦 <b>Добавление нового товара</b>\n\n"
        "Выберите категорию товара:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return CATEGORY


async def process_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора категории"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_add':
        await query.edit_message_text("❌ Добавление товара отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    category_id = int(query.data.replace('add_cat_', ''))
    context.user_data['new_product']['category_id'] = category_id

    # Получаем информацию о категории
    category = db.get_category_by_id(category_id)

    await query.edit_message_text(
        f"📦 <b>Добавление товара</b>\n\n"
        f"Категория: <b>{category['name']}</b>\n\n"
        "📝 Введите название товара:\n"
        "<i>Пример: HQD Cuvie Plus 2500 тяг</i>",
        parse_mode='HTML'
    )

    return NAME


async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия товара"""
    name = update.message.text
    context.user_data['new_product']['name'] = name

    await update.message.reply_text(
        "💰 Введите цену товара в рублях (только число):\n\n"
        "<i>Пример: 1299</i>",
        parse_mode='HTML'
    )

    return PRICE


async def process_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка цены товара"""
    try:
        price = int(update.message.text)
        if price <= 0:
            raise ValueError

        context.user_data['new_product']['price'] = price

        await update.message.reply_text(
            "📋 Введите описание товара:\n\n"
            "<i>Пример: 2500 тяг, 15 вкусов, тип: одноразовый, никотин: 20мг/мл</i>\n\n"
            "<i>Или отправьте /skip чтобы пропустить</i>",
            parse_mode='HTML'
        )

        return DESCRIPTION

    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректную цену (целое число больше 0):",
            parse_mode='HTML'
        )
        return PRICE


async def process_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания товара"""
    description = update.message.text
    context.user_data['new_product']['description'] = description

    await update.message.reply_text(
        "📸 <b>Добавление фотографии товара</b>\n\n"
        "Отправьте фотографию товара.\n\n"
        "<i>Или отправьте /skip чтобы пропустить добавление фото</i>",
        parse_mode='HTML'
    )

    return PHOTO


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск описания"""
    context.user_data['new_product']['description'] = ""

    await update.message.reply_text(
        "📸 <b>Добавление фотографии товара</b>\n\n"
        "Отправьте фотографию товара.\n\n"
        "<i>Или отправьте /skip чтобы пропустить добавление фото</i>",
        parse_mode='HTML'
    )

    return PHOTO


async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографии товара"""
    if update.message.photo:
        # Берем последнее (самое большое) фото
        photo = update.message.photo[-1]
        context.user_data['new_product']['photo_id'] = photo.file_id

        await confirm_product(update, context)
        return CONFIRM
    else:
        await update.message.reply_text("❌ Пожалуйста, отправьте фотографию или используйте /skip")
        return PHOTO


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск добавления фото"""
    context.user_data['new_product']['photo_id'] = None

    await confirm_product(update, context)
    return CONFIRM


async def confirm_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение добавления товара"""
    product_data = context.user_data['new_product']

    # Получаем название категории
    category = db.get_category_by_id(product_data['category_id'])

    # Формируем сообщение с информацией о товаре
    text = (
        f"✅ <b>Подтвердите добавление товара</b>\n\n"
        f"<b>Категория:</b> {category['name']}\n"
        f"<b>Название:</b> {product_data['name']}\n"
        f"<b>Цена:</b> {product_data['price']}₽\n"
        f"<b>Описание:</b> {product_data.get('description', 'Нет описания')}\n"
        f"<b>Фото:</b> {'Есть' if product_data.get('photo_id') else 'Нет'}\n\n"
        "<i>Всё верно?</i>"
    )

    # Создаем клавиатуру подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, добавить", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_product")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_no")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Если есть фото, отправляем его с подписью
    if product_data.get('photo_id'):
        await update.message.reply_photo(
            photo=product_data['photo_id'],
            caption=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    return CONFIRM


async def save_product_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение товара в базу данных"""
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm_yes':
        product_data = context.user_data['new_product']

        # Сохраняем товар в БД
        product_id = db.add_product(
            category_id=product_data['category_id'],
            name=product_data['name'],
            price=product_data['price'],
            description=product_data.get('description', ''),
            photo_id=product_data.get('photo_id'),
            stock=product_data.get('stock', 0)
        )

        if product_id:
            await query.edit_message_text(
                f"✅ <b>Товар успешно добавлен!</b>\n\n"
                f"ID товара: <code>{product_id}</code>\n"
                f"Название: {product_data['name']}\n"
                f"Цена: {product_data['price']}₽\n\n"
                f"<i>Товар сохранен в базе данных и доступен пользователям.</i>",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "❌ <b>Ошибка при сохранении товара!</b>\n\n"
                "<i>Попробуйте еще раз или обратитесь к администратору.</i>",
                parse_mode='HTML'
            )

        # Очищаем временные данные
        context.user_data.clear()
        return ConversationHandler.END

    elif query.data == 'confirm_no':
        await query.edit_message_text("❌ Добавление товара отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    elif query.data == 'edit_product':
        await show_edit_options(update, context)
        return EDIT_CHOICE


async def show_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать опции редактирования"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data="edit_name")],
        [InlineKeyboardButton("💰 Цена", callback_data="edit_price")],
        [InlineKeyboardButton("📋 Описание", callback_data="edit_description")],
        [InlineKeyboardButton("📸 Фото", callback_data="edit_photo")],
        [InlineKeyboardButton("📦 Категория", callback_data="edit_category")],
        [InlineKeyboardButton("✅ Всё верно, сохранить", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_no")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✏️ <b>Что вы хотите отредактировать?</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


# ==================== УДАЛЕНИЕ ТОВАРОВ ====================

async def delete_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для удаления товара"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    if not context.args:
        # Показать список товаров для удаления
        products = db.get_all_products(active_only=True)

        if not products:
            await update.message.reply_text("📦 В базе данных нет товаров.")
            return

        text = "🗑️ <b>Выберите товар для удаления:</b>\n\n"
        keyboard = []

        for product in products[:20]:  # Показываем первые 20 товаров
            btn_text = f"{product['name']} - {product['price']}₽"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f"del_prod_{product['id']}")
            ])

        # Если товаров много, добавляем пагинацию
        if len(products) > 20:
            keyboard.append([
                InlineKeyboardButton("▶️ Следующие", callback_data="del_next_page")
            ])

        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return

    # Если передан ID товара
    try:
        product_id = int(context.args[0])
        product = db.get_product_by_id(product_id)

        if not product:
            await update.message.reply_text("❌ Товар не найден.")
            return

        await confirm_delete(update, context, product)

    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Используйте: /delete_product [ID_товара]")


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, product: Dict = None):
    """Подтверждение удаления товара"""
    if not product and update.callback_query:
        query = update.callback_query
        await query.answer()

        if query.data.startswith('del_prod_'):
            product_id = int(query.data.replace('del_prod_', ''))
            product = db.get_product_by_id(product_id)

        elif query.data == 'cancel_delete':
            await query.edit_message_text("❌ Удаление отменено.")
            return

    if not product:
        await update.message.reply_text("❌ Товар не найден.")
        return

    # Сохраняем ID товара в контексте
    context.user_data['delete_product_id'] = product['id']

    text = (
        f"🗑️ <b>Подтвердите удаление товара</b>\n\n"
        f"<b>ID:</b> {product['id']}\n"
        f"<b>Название:</b> {product['name']}\n"
        f"<b>Цена:</b> {product['price']}₽\n"
        f"<b>Категория:</b> {product['category_name']}\n\n"
        "<i>Товар будет помечен как неактивный и скрыт из каталога.</i>"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="delete_confirm_yes")],
        [InlineKeyboardButton("❌ Нет, отмена", callback_data="delete_confirm_no")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение удаления товара"""
    query = update.callback_query
    await query.answer()

    if query.data == 'delete_confirm_yes':
        product_id = context.user_data.get('delete_product_id')

        if not product_id:
            await query.edit_message_text("❌ Ошибка: ID товара не найден.")
            return

        # Удаляем товар из БД
        success = db.delete_product(product_id)

        if success:
            await query.edit_message_text(
                f"✅ <b>Товар успешно удален!</b>\n\n"
                f"ID товара: {product_id}\n"
                f"<i>Товар помечен как неактивный и скрыт из каталога.</i>",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                "❌ <b>Ошибка при удалении товара!</b>\n\n"
                "<i>Попробуйте еще раз или обратитесь к администратору.</i>",
                parse_mode='HTML'
            )

        # Очищаем временные данные
        context.user_data.pop('delete_product_id', None)

    elif query.data == 'delete_confirm_no':
        await query.edit_message_text("❌ Удаление отменено.")


# ==================== ПРОСМОТР ТОВАРОВ ====================

async def list_products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра всех товаров"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    products = db.get_all_products(active_only=True)

    if not products:
        await update.message.reply_text("📦 В базе данных нет товаров.")
        return

    text = "📦 <b>Список всех товаров:</b>\n\n"

    for product in products:
        text += (
            f"<b>ID:</b> {product['id']}\n"
            f"<b>Название:</b> {product['name']}\n"
            f"<b>Цена:</b> {product['price']}₽\n"
            f"<b>Категория:</b> {product['category_name']}\n"
            f"<b>Фото:</b> {'✅ Есть' if product.get('photo_id') else '❌ Нет'}\n"
            f"{'-' * 30}\n"
        )

    text += f"\n<b>Всего товаров:</b> {len(products)}"

    # Разбиваем на части, если сообщение слишком длинное
    if len(text) > 4000:
        parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='HTML')
    else:
        await update.message.reply_text(text, parse_mode='HTML')


# ==================== ПОИСК ТОВАРОВ ====================

async def search_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск товаров по названию"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Поиск товаров</b>\n\n"
            "Использование: /search_product [название]\n\n"
            "Пример: /search_product HQD",
            parse_mode='HTML'
        )
        return

    search_query = ' '.join(context.args)
    products = db.search_products(search_query)

    if not products:
        await update.message.reply_text(
            f"🔍 <b>По запросу '{search_query}' ничего не найдено.</b>",
            parse_mode='HTML'
        )
        return

    text = f"🔍 <b>Результаты поиска по '{search_query}':</b>\n\n"

    for product in products[:10]:  # Показываем первые 10 результатов
        text += (
            f"<b>ID:</b> {product['id']}\n"
            f"<b>Название:</b> {product['name']}\n"
            f"<b>Цена:</b> {product['price']}₽\n"
            f"<b>Категория:</b> {product['category_name']}\n"
            f"{'-' * 20}\n"
        )

    if len(products) > 10:
        text += f"\n<i>Показано 10 из {len(products)} результатов</i>"

    await update.message.reply_text(text, parse_mode='HTML')


# ==================== ConversationHandler ДЛЯ ДОБАВЛЕНИЯ ТОВАРА ====================

add_product_conversation = ConversationHandler(
    entry_points=[CommandHandler('add_product', start_add_product)],
    states={
        CATEGORY: [CallbackQueryHandler(process_category, pattern='^(add_cat_|cancel_add)')],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_name)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_price)],
        DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_description),
            CommandHandler('skip', skip_description),
        ],
        PHOTO: [
            MessageHandler(filters.PHOTO, process_photo),
            CommandHandler('skip', skip_photo),
        ],
        CONFIRM: [CallbackQueryHandler(save_product_to_db, pattern='^(confirm_yes|confirm_no|edit_product)')],
        EDIT_CHOICE: [CallbackQueryHandler(save_product_to_db, pattern='^(confirm_yes|confirm_no)')],
    },
    fallbacks=[
        CommandHandler('cancel', lambda u, c: ConversationHandler.END),
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^cancel_'),
    ],
)