# product_manager.py - ПОЛНЫЙ РАБОЧИЙ КОД
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)
from database import db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CATEGORY, NAME, PRICE, DESCRIPTION, PHOTO, CONFIRM, EDIT_CHOICE = range(7)


# ==================== ОСНОВНЫЕ ФУНКЦИИ ДОБАВЛЕНИЯ ТОВАРА ====================



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
        await update.message.reply_text("❌ Нет доступных категорий.")
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
        "Выберите категорию:",
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

    # Проверяем, редактируем ли мы или добавляем новый товар
    if context.user_data.get('edit_field') == 'category':
        context.user_data['new_product']['category_id'] = category_id
        # После редактирования возвращаем к подтверждению
        await confirm_product(update, context)
        return CONFIRM
    else:
        context.user_data['new_product']['category_id'] = category_id
        await query.edit_message_text(
            "📝 Введите название товара:\n\n"
            "<i>Пример: HQD Cuvie Plus 2500 тяг</i>",
            parse_mode='HTML'
        )
        return NAME


async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия товара"""
    name = update.message.text

    if context.user_data.get('edit_field') == 'name':
        context.user_data['new_product']['name'] = name
        # После редактирования возвращаем к подтверждению
        await confirm_product(update, context)
        return CONFIRM
    else:
        context.user_data['new_product']['name'] = name
        await update.message.reply_text(
            "💰 Введите цену в рублях (только число):\n\n"
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

        if context.user_data.get('edit_field') == 'price':
            context.user_data['new_product']['price'] = price
            await confirm_product(update, context)
            return CONFIRM
        else:
            context.user_data['new_product']['price'] = price
            await update.message.reply_text(
                "📋 Введите описание товара:\n\n"
                "<i>Пример: 2500 тяг, 15 вкусов, тип: одноразовый</i>\n\n"
                "Или отправьте /skip чтобы пропустить",
                parse_mode='HTML'
            )
            return DESCRIPTION

    except ValueError:
        await update.message.reply_text(
            "❌ Некорректная цена! Введите целое число больше 0:",
            parse_mode='HTML'
        )
        return PRICE


async def process_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания товара"""
    description = update.message.text

    if context.user_data.get('edit_field') == 'description':
        context.user_data['new_product']['description'] = description
        await confirm_product(update, context)
        return CONFIRM
    else:
        context.user_data['new_product']['description'] = description
        await update.message.reply_text(
            "📸 Отправьте фото товара:\n\n"
            "Или отправьте /skip чтобы пропустить",
            parse_mode='HTML'
        )
        return PHOTO


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск описания"""
    context.user_data['new_product']['description'] = ""

    if context.user_data.get('edit_field') == 'description':
        await confirm_product(update, context)
        return CONFIRM
    else:
        await update.message.reply_text(
            "📸 Отправьте фото товара:\n\n"
            "Или отправьте /skip чтобы пропустить",
            parse_mode='HTML'
        )
        return PHOTO


async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографии товара"""
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data['new_product']['photo_id'] = photo.file_id

    if context.user_data.get('edit_field') == 'photo':
        await confirm_product(update, context)
        return CONFIRM
    else:
        await confirm_product(update, context)
        return CONFIRM


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск фото"""
    context.user_data['new_product']['photo_id'] = None

    if context.user_data.get('edit_field') == 'photo':
        await confirm_product(update, context)
        return CONFIRM
    else:
        await confirm_product(update, context)
        return CONFIRM


async def confirm_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ информации о товаре и предложение редактирования"""
    product_data = context.user_data['new_product']

    # Получаем название категории - ИСПРАВЛЕННАЯ СТРОКА
    category_name = db.get_category_name(product_data['category_id'])  # Изменено!

    # Формируем сообщение
    text = (
        f"📦 <b>Информация о товаре</b>\n\n"
        f"<b>Категория:</b> {category_name}\n"  # Изменено!
        f"<b>Название:</b> {product_data['name']}\n"
        f"<b>Цена:</b> {product_data['price']}₽\n"
        f"<b>Описание:</b> {product_data.get('description', 'Нет описания')}\n"
        f"<b>Фото:</b> {'✅ Есть' if product_data.get('photo_id') else '❌ Нет'}\n\n"
    )

    # Если это редактирование, убираем флаг редактирования
    if 'edit_field' in context.user_data:
        del context.user_data['edit_field']
        text += "✅ <b>Изменения сохранены!</b>\n\n"

    text += (
        "<b>Что дальше?</b>\n\n"
        "Отправьте:\n"
        "• <code>save</code> - сохранить товар\n"
        "• <code>edit</code> - редактировать\n"
        "• <code>cancel</code> - отменить\n\n"
        "Или команду /cancel"
    )

    await update.message.reply_text(text, parse_mode='HTML')
    return CONFIRM


async def save_product_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальное сохранение товара в БД"""
    user_input = update.message.text.strip().lower()

    if user_input == 'save':
        product_data = context.user_data['new_product']

        # ОТЛАДКА: выводим что пытаемся сохранить
        logger.info(f"Пытаемся сохранить товар: {product_data}")

        try:
            # ПОМЕНЯЙТЕ ЗДЕСЬ: добавление товара должно использовать category_id, а не category
            category_name = db.get_category_name(product_data['category_id'])  # Получаем имя категории

            product_id = db.add_product(
                category=category_name,  # Передаем имя категории, а не ID
                name=product_data['name'],
                price=product_data['price'],
                description=product_data.get('description', ''),
                photo_id=product_data.get('photo_id')
            )

            logger.info(f"Результат сохранения: ID = {product_id}")

            if product_id and product_id > 0:
                await update.message.reply_text(
                    f"✅ <b>Товар успешно сохранен!</b>\n\n"
                    f"<b>ID:</b> <code>{product_id}</code>\n"
                    f"<b>Название:</b> {product_data['name']}\n"
                    f"<b>Цена:</b> {product_data['price']}₽\n"
                    f"<b>Категория:</b> {category_name}\n\n"
                    f"Добавить еще товар: /add_product",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ <b>Ошибка при сохранении!</b>\n"
                    "ID товара не был возвращен.\n\n"
                    "Попробуйте еще раз: /add_product",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"Ошибка при сохранении товара: {e}")
            await update.message.reply_text(
                f"❌ <b>Критическая ошибка!</b>\n\n"
                f"Ошибка: {str(e)}\n\n"
                "Попробуйте еще раз: /add_product",
                parse_mode='HTML'
            )

        context.user_data.clear()
        return ConversationHandler.END

    # ... остальной код функции остается без изменений ...

    elif user_input == 'edit':
        await update.message.reply_text(
            "✏️ <b>Что вы хотите отредактировать?</b>\n\n"
            "Отправьте номер:\n"
            "1. 📝 Название\n"
            "2. 💰 Цена\n"
            "3. 📋 Описание\n"
            "4. 📸 Фото\n"
            "5. 📦 Категория\n\n"
            "Или /cancel для отмены"
        )
        return EDIT_CHOICE

    elif user_input == 'cancel':
        await update.message.reply_text("❌ Добавление товара отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "❌ Не понял команду. Отправьте:\n"
            "• <code>save</code> - сохранить\n"
            "• <code>edit</code> - редактировать\n"
            "• <code>cancel</code> - отменить"
        )
        return CONFIRM


async def process_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора что редактировать (текстовый ввод)"""
    choice = update.message.text.strip()

    if choice == '1':
        await update.message.reply_text("✏️ Введите новое название товара:")
        context.user_data['edit_field'] = 'name'
        return NAME
    elif choice == '2':
        await update.message.reply_text("💰 Введите новую цену:")
        context.user_data['edit_field'] = 'price'
        return PRICE
    elif choice == '3':
        await update.message.reply_text("📋 Введите новое описание:")
        context.user_data['edit_field'] = 'description'
        return DESCRIPTION
    elif choice == '4':
        await update.message.reply_text("📸 Отправьте новое фото:")
        context.user_data['edit_field'] = 'photo'
        return PHOTO
    elif choice == '5':
        await update.message.reply_text("📦 Выберите новую категорию:")
        context.user_data['edit_field'] = 'category'
        return CATEGORY
    else:
        await update.message.reply_text(
            "❌ Неверный выбор! Отправьте номер от 1 до 5:\n\n"
            "1. 📝 Название\n"
            "2. 💰 Цена\n"
            "3. 📋 Описание\n"
            "4. 📸 Фото\n"
            "5. 📦 Категория\n\n"
            "Или отправьте /cancel для отмены"
        )
        return EDIT_CHOICE


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления товара"""
    await update.message.reply_text("❌ Добавление товара отменено.")
    context.user_data.clear()
    return ConversationHandler.END


# ==================== ConversationHandler для добавления товара ====================

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
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_product_final)],
        EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_choice)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel_add),
    ],
    per_message=False,
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


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, product: dict = None):
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