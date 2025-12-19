# Админка
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)
from database import db
import logging

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CATEGORY, NAME, PRICE, DESCRIPTION, PHOTO = range(5)


# ==================== АДМИН ПАНЕЛЬ (/admin команда) ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора - команда /admin"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    user_count = 0  # Пока заглушка
    product_count = len(db.get_all_products())

    text = (
        f"⚙️ <b>Панель администратора VapeShop</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Пользователей: {user_count}\n"
        f"• Товаров: {product_count}\n\n"
        "<b>📦 Управление товарами:</b>\n"
        "/add_product - Добавить товар\n"
        "/delete_product - Удалить товар\n"
        "/list_products - Список всех товаров\n"
        "/search_product [текст] - Поиск товара\n\n"
        "<b>📢 Рассылка:</b>\n"
        "/broadcast - Рассылка сообщения\n\n"
        "<b>👥 Управление пользователями:</b>\n"
        "/user_info [ID] - Информация о пользователе\n"
        "/make_admin [ID] - Назначить админом\n\n"
        "<b>📊 Статистика:</b>\n"
        "/stats - Подробная статистика"
    )

    await update.message.reply_text(text, parse_mode='HTML')


# ==================== ДОБАВЛЕНИЕ ТОВАРА ====================

async def add_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add_product - запуск добавления товара"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return ConversationHandler.END

    # Очищаем старые данные
    context.user_data.clear()

    # Показываем категории
    categories = db.get_categories()
    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat['name'], callback_data=f'add_cat_{cat["id"]}')])

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='add_cancel')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📦 <b>Добавление товара</b>\n\n"
        "Выберите категорию:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return CATEGORY


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор категории для добавления товара"""
    query = update.callback_query
    await query.answer()

    if query.data == 'add_cancel':
        await query.edit_message_text("❌ Добавление товара отменено")
        return ConversationHandler.END

    # Получаем ID категории
    cat_id = int(query.data.replace('add_cat_', ''))

    # Получаем название категории
    categories = db.get_categories()
    category = next((c for c in categories if c['id'] == cat_id), None)

    if not category:
        await query.edit_message_text("❌ Ошибка: категория не найдена")
        return ConversationHandler.END

    # Сохраняем категорию
    context.user_data['category'] = category['name']

    await query.edit_message_text(
        f"✅ Категория: <b>{category['name']}</b>\n\n"
        "📝 Введите название товара:",
        parse_mode='HTML'
    )

    return NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия товара"""
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text("❌ Название не может быть пустым. Введите название:")
        return NAME

    context.user_data['name'] = name

    await update.message.reply_text(
        f"✅ Название: <b>{name}</b>\n\n"
        "💰 Введите цену товара (только число, в рублях):",
        parse_mode='HTML'
    )

    return PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод цены товара"""
    try:
        price = int(update.message.text.strip())
        if price <= 0:
            raise ValueError

        context.user_data['price'] = price

        await update.message.reply_text(
            f"✅ Цена: <b>{price}₽</b>\n\n"
            "📝 Введите описание товара:\n"
            "<i>Или отправьте /skip чтобы пропустить</i>",
            parse_mode='HTML'
        )

        return DESCRIPTION

    except ValueError:
        await update.message.reply_text(
            "❌ Неверная цена! Введите целое число больше 0:",
            parse_mode='HTML'
        )
        return PRICE


async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод описания товара"""
    description = update.message.text.strip()
    context.user_data['description'] = description

    await update.message.reply_text(
        "📸 Отправьте фотографию товара:\n"
        "<i>Или отправьте /skip чтобы пропустить</i>",
        parse_mode='HTML'
    )

    return PHOTO


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск описания"""
    context.user_data['description'] = ""

    await update.message.reply_text(
        "📸 Отправьте фотографию товара:\n"
        "<i>Или отправьте /skip чтобы пропустить</i>",
        parse_mode='HTML'
    )

    return PHOTO


async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление фото и сохранение товара"""
    if update.message.photo:
        # Берем последнее (самое качественное) фото
        photo = update.message.photo[-1]
        context.user_data['photo_id'] = photo.file_id

    # Получаем все данные
    product_data = context.user_data

    # Сохраняем товар в БД
    product_id = db.add_product(
        category=product_data['category'],
        name=product_data['name'],
        price=product_data['price'],
        description=product_data.get('description', ''),
        photo_id=product_data.get('photo_id')
    )

    if product_id:
        await update.message.reply_text(
            f"✅ <b>Товар успешно добавлен!</b>\n\n"
            f"📦 <b>Название:</b> {product_data['name']}\n"
            f"💰 <b>Цена:</b> {product_data['price']}₽\n"
            f"🏷️ <b>Категория:</b> {product_data['category']}\n"
            f"🆔 <b>ID товара:</b> <code>{product_id}</code>\n\n"
            f"Добавить еще товар: /add_product",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Ошибка при сохранении товара!</b>\n\n"
            "Попробуйте еще раз: /add_product",
            parse_mode='HTML'
        )

    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск фото и сохранение товара"""
    # Получаем все данные
    product_data = context.user_data

    # Сохраняем товар в БД без фото
    product_id = db.add_product(
        category=product_data['category'],
        name=product_data['name'],
        price=product_data['price'],
        description=product_data.get('description', ''),
        photo_id=None
    )

    if product_id:
        await update.message.reply_text(
            f"✅ <b>Товар успешно добавлен!</b>\n\n"
            f"📦 <b>Название:</b> {product_data['name']}\n"
            f"💰 <b>Цена:</b> {product_data['price']}₽\n"
            f"🏷️ <b>Категория:</b> {product_data['category']}\n"
            f"🆔 <b>ID товара:</b> <code>{product_id}</code>\n\n"
            f"Добавить еще товар: /add_product",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Ошибка при сохранении товара!</b>\n\n"
            "Попробуйте еще раз: /add_product",
            parse_mode='HTML'
        )

    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления товара"""
    await update.message.reply_text("❌ Добавление товара отменено.")
    context.user_data.clear()
    return ConversationHandler.END


# ==================== ConversationHandler для добавления товара ====================

add_product_conversation = ConversationHandler(
    entry_points=[CommandHandler('add_product', add_product_command)],
    states={
        CATEGORY: [CallbackQueryHandler(add_category, pattern='^add_cat_|add_cancel$')],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
        DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_description),
            CommandHandler('skip', skip_description),
        ],
        PHOTO: [
            MessageHandler(filters.PHOTO, add_photo),
            CommandHandler('skip', skip_photo),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_add)],
    per_message=False,
)


# ==================== УДАЛЕНИЕ ТОВАРА ====================

async def delete_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete_product"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    if not context.args:
        # Показываем список товаров для удаления
        products = db.get_all_products()

        if not products:
            await update.message.reply_text("📦 Нет товаров для удаления")
            return

        text = "🗑️ <b>Выберите товар для удаления:</b>\n\n"
        keyboard = []

        for prod in products[:15]:  # Показываем первые 15 товаров
            btn_text = f"{prod['name']} - {prod['price']}₽"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f'del_{prod["id"]}')
            ])

        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='del_cancel')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return

    # Если передан ID товара напрямую
    try:
        product_id = int(context.args[0])
        product = db.get_product_by_id(product_id)

        if not product:
            await update.message.reply_text("❌ Товар не найден")
            return

        # Сразу удаляем
        if db.delete_product(product_id):
            await update.message.reply_text(
                f"✅ Товар удален!\n\n"
                f"Название: {product['name']}\n"
                f"Цена: {product['price']}₽\n"
                f"ID: {product_id}",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Ошибка при удалении товара")

    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Используйте: /delete_product [ID_товара]")


async def delete_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок удаления товара"""
    query = update.callback_query
    await query.answer()

    if query.data == 'del_cancel':
        await query.edit_message_text("❌ Удаление отменено")
        return

    if query.data.startswith('del_'):
        product_id = int(query.data.replace('del_', ''))
        product = db.get_product_by_id(product_id)

        if not product:
            await query.edit_message_text("❌ Товар не найден")
            return

        # Показываем подтверждение удаления
        context.user_data['delete_product_id'] = product_id

        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data='confirm_delete')],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data='cancel_delete')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"🗑️ <b>Подтвердите удаление</b>\n\n"
            f"📦 <b>Товар:</b> {product['name']}\n"
            f"💰 <b>Цена:</b> {product['price']}₽\n"
            f"🏷️ <b>Категория:</b> {product['category']}\n"
            f"🆔 <b>ID:</b> {product_id}\n\n"
            f"Удалить этот товар?",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    elif query.data == 'confirm_delete':
        product_id = context.user_data.get('delete_product_id')

        if not product_id:
            await query.edit_message_text("❌ Ошибка: ID товара не найден")
            return

        # Удаляем товар
        if db.delete_product(product_id):
            await query.edit_message_text(f"✅ Товар {product_id} успешно удален!")
        else:
            await query.edit_message_text("❌ Ошибка при удалении товара")

        # Очищаем временные данные
        if 'delete_product_id' in context.user_data:
            del context.user_data['delete_product_id']

    elif query.data == 'cancel_delete':
        await query.edit_message_text("❌ Удаление отменено")
        if 'delete_product_id' in context.user_data:
            del context.user_data['delete_product_id']


# ==================== СПИСОК ТОВАРОВ ====================

async def list_products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list_products"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    products = db.get_all_products()

    if not products:
        await update.message.reply_text("📦 В базе данных нет товаров")
        return

    text = "<b>📦 Список всех товаров:</b>\n\n"

    current_category = None
    for product in products:
        if product['category'] != current_category:
            current_category = product['category']
            text += f"\n<b>🏷️ {current_category}:</b>\n"

        text += f"🆔 <code>{product['id']}</code> - {product['name']} - {product['price']}₽\n"
        if product.get('photo_id'):
            text += "   📸 Есть фото\n"

    text += f"\n<b>Всего товаров:</b> {len(products)}"

    # Разбиваем на части если сообщение слишком длинное
    if len(text) > 4000:
        parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='HTML')
    else:
        await update.message.reply_text(text, parse_mode='HTML')


# ==================== ПОИСК ТОВАРА ====================

async def search_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search_product"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Поиск товаров</b>\n\n"
            "Использование: /search_product [текст]\n\n"
            "Пример:\n"
            "<code>/search_product HQD</code>\n"
            "<code>/search_product жидкость</code>",
            parse_mode='HTML'
        )
        return

    search_query = ' '.join(context.args)
    products = db.search_products(search_query)

    if not products:
        await update.message.reply_text(
            f"🔍 По запросу '<b>{search_query}</b>' ничего не найдено",
            parse_mode='HTML'
        )
        return

    text = f"🔍 <b>Результаты поиска '{search_query}':</b>\n\n"

    for product in products[:10]:  # Показываем первые 10 результатов
        text += f"🆔 <code>{product['id']}</code> - {product['name']} - {product['price']}₽\n"
        text += f"   🏷️ {product['category']}\n"

    if len(products) > 10:
        text += f"\n<i>Показано 10 из {len(products)} результатов</i>"

    await update.message.reply_text(text, parse_mode='HTML')


# ==================== СТАТИСТИКА ====================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - подробная статистика магазина"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    # Добавляем текущее время
    from datetime import datetime
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M')

    products = db.get_all_products()
    categories = db.get_categories()

    # НОВОЕ: реальная статистика пользователей
    user_count = db.get_user_count()
    admin_count = db.get_admin_count()
    regular_user_count = user_count - admin_count

    # Считаем товары по категориям
    category_stats = {}
    products_with_photo = 0
    total_price = 0

    for product in products:
        cat = product['category']
        category_stats[cat] = category_stats.get(cat, 0) + 1

        if product.get('photo_id'):
            products_with_photo += 1

        total_price += product['price']

    text = "📊 <b>Детальная статистика магазина</b>\n\n"

    # Пользователи
    text += f"<b>👥 Пользователи:</b>\n"
    text += f"• Всего: {user_count}\n"
    text += f"• Администраторов: {admin_count}\n"
    text += f"• Обычных пользователей: {regular_user_count}\n\n"

    # Товары
    text += f"<b>📦 Товары:</b>\n"
    text += f"• Всего: {len(products)}\n"
    text += f"• С фото: {products_with_photo}\n"

    if products:
        avg_price = total_price / len(products)
        text += f"• Средняя цена: {avg_price:.0f}₽\n\n"
    else:
        text += "\n"

    # Категории
    if categories:
        text += f"<b>🏷️ Категории:</b>\n"
        for category in categories:
            count = category_stats.get(category['name'], 0)
            text += f"• {category['emoji']} {category['name']}: {count} товаров\n"

    # Добавляем список админов
    db.cursor.execute("SELECT user_id, first_name, username FROM users WHERE is_admin = 1")
    admins = db.cursor.fetchall()

    if admins:
        text += f"\n<b>👑 Администраторы ({len(admins)}):</b>\n"
        for admin in admins:
            name = admin['first_name'] or f"ID: {admin['user_id']}"
            username = f" @{admin['username']}" if admin['username'] else ""
            text += f"• {name}{username}\n"

    await update.message.reply_text(text, parse_mode='HTML')


# ==================== РАССЫЛКА ====================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /broadcast"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    if not context.args:
        await update.message.reply_text(
            "📢 <b>Рассылка сообщений</b>\n\n"
            "Использование: /broadcast [текст сообщения]\n\n"
            "Пример:\n"
            "<code>/broadcast 🔥 Акция! Скидка 20% на все жидкости!</code>\n\n"
            "<i>Сообщение будет отправлено всем пользователям бота</i>",
            parse_mode='HTML'
        )
        return

    message_text = ' '.join(context.args)

    # Здесь будет код рассылки
    # Пока просто показываем что бы отправилось
    await update.message.reply_text(
        f"📢 <b>Рассылка подготовлена:</b>\n\n"
        f"{message_text}\n\n"
        f"<i>Функция рассылки в разработке</i>",
        parse_mode='HTML'
    )


# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /user_info - подробная информация о пользователе"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    target_id = user_id  # По умолчанию информация о себе

    if context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный ID пользователя")
            return

    user = db.get_user_by_id(target_id)

    if not user:
        # Попробуем получить информацию через Telegram API как запасной вариант
        try:
            chat_member = await context.bot.get_chat_member(target_id, target_id)
            user_info = chat_member.user

            # Сохраняем в БД для будущего использования
            db.add_user(
                user_id=user_info.id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )

            text = (
                f"👤 <b>Информация о пользователе (из Telegram)</b>\n\n"
                f"🆔 <b>ID:</b> {user_info.id}\n"
                f"👤 <b>Имя:</b> {user_info.first_name or 'Не указано'}\n"
                f"👥 <b>Фамилия:</b> {user_info.last_name or 'Не указана'}\n"
                f"📱 <b>Username:</b> @{user_info.username or 'Не указан'}\n"
                f"📅 <b>Статус в базе:</b> Не зарегистрирован в боте\n\n"
                f"<i>Пользователь добавлен в базу данных</i>"
            )

            await update.message.reply_text(text, parse_mode='HTML')
            return

        except Exception as e:
            await update.message.reply_text(
                f"❌ Пользователь с ID {target_id} не найден.\n"
                f"Ошибка: {str(e)}"
            )
            return

    # Форматируем данные для красивого отображения
    username_display = f"@{user['username']}" if user['username'] != 'Не указано' else user['username']

    # Обработка даты
    join_date = user.get('join_date', 'Неизвестно')
    if join_date and isinstance(join_date, str):
        try:
            from datetime import datetime
            if 'T' in join_date:  # SQLite формат с T
                dt = datetime.strptime(join_date.replace('T', ' '), '%Y-%m-%d %H:%M:%S')
            else:
                dt = datetime.strptime(join_date, '%Y-%m-%d %H:%M:%S')
            join_date = dt.strftime('%d.%m.%Y %H:%M')
        except:
            pass

    text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user['user_id']}</code>\n"
        f"👤 <b>Имя:</b> {user['first_name']}\n"
        f"👥 <b>Фамилия:</b> {user['last_name']}\n"
        f"📱 <b>Username:</b> {username_display}\n"
        f"👑 <b>Статус:</b> {'Администратор 👑' if user.get('is_admin') else 'Пользователь 👤'}\n"
        f"📅 <b>Дата регистрации:</b> {join_date}\n\n"
    )

    # Добавляем информацию о последней активности (если есть)
    if 'last_activity' in user and user['last_activity']:
        text += f"🕐 <b>Последняя активность:</b> {user['last_activity']}\n"

    # Кнопка для назначения админом
    keyboard = []
    if not user.get('is_admin'):
        keyboard.append([
            InlineKeyboardButton(
                "👑 Назначить админом",
                callback_data=f"make_admin_{user['user_id']}"
            )
        ])

    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, parse_mode='HTML')


async def make_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /make_admin"""
    user_id = update.effective_user.id

    # Только главный администратор может назначать других
    MAIN_ADMIN_ID = 907331808  # Ваш ID

    if user_id != MAIN_ADMIN_ID:
        await update.message.reply_text("⛔ Только главный администратор может назначать других!")
        return

    if not context.args:
        await update.message.reply_text(
            "👑 <b>Назначение администратора</b>\n\n"
            "Использование: /make_admin [ID_пользователя]\n\n"
            "Пример:\n"
            "<code>/make_admin 987654321</code>\n\n"
            "Текущие администраторы: /list_admins",
            parse_mode='HTML'
        )
        return

    try:
        new_admin_id = int(context.args[0])

        # Пробуем получить информацию о пользователе из Telegram
        try:
            chat_member = await context.bot.get_chat_member(new_admin_id, new_admin_id)
            user_info = chat_member.user

            success = db.add_admin(
                user_id=user_info.id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name
            )

            if success:
                await update.message.reply_text(
                    f"✅ <b>Пользователь назначен администратором!</b>\n\n"
                    f"👤 Имя: {user_info.first_name or 'Не указано'}\n"
                    f"👥 Фамилия: {user_info.last_name or 'Не указана'}\n"
                    f"📱 Username: @{user_info.username or 'Нет'}\n"
                    f"🆔 ID: <code>{new_admin_id}</code>\n\n"
                    f"Проверить: /user_info {new_admin_id}",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("❌ Ошибка при назначении администратора")

        except Exception as e:
            # Если не удалось получить данные из Telegram, добавляем только по ID
            logger.warning(f"Не удалось получить данные пользователя {new_admin_id} из Telegram: {e}")

            success = db.add_admin(user_id=new_admin_id)

            if success:
                await update.message.reply_text(
                    f"✅ Пользователь {new_admin_id} назначен администратором!\n\n"
                    f"<i>Данные пользователя не получены из Telegram. "
                    f"Они обновятся когда пользователь запустит бота.</i>",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("❌ Ошибка при назначении администратора")

    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя")


# admin.py - добавьте эту функцию в конец файла (или в начало, перед другими функциями)

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки админ-панели"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not db.is_admin(user_id):
        await query.answer("⛔ У вас нет прав администратора!", show_alert=True)
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

    keyboard = [[InlineKeyboardButton("⬅️ В меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


# В admin.py добавьте эту функцию:

async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list_admins - список всех администраторов"""
    user_id = update.effective_user.id

    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return

    try:
        # Получаем всех админов из БД
        db.cursor.execute("SELECT * FROM users WHERE is_admin = 1 ORDER BY join_date")
        admins = db.cursor.fetchall()

        if not admins:
            await update.message.reply_text("👑 В системе нет администраторов.")
            return

        text = "👑 <b>Список администраторов:</b>\n\n"

        for i, admin in enumerate(admins, 1):
            admin_dict = dict(admin)

            # Форматируем дату
            join_date = admin_dict.get('join_date', 'Неизвестно')
            if join_date:
                join_date = db.format_moscow_time(join_date)

            text += f"{i}. <b>{admin_dict.get('first_name', 'Неизвестно')} {admin_dict.get('last_name', '')}</b>\n"
            text += f"   👤 Username: @{admin_dict.get('username', 'Нет')}\n"
            text += f"   🆔 ID: <code>{admin_dict['user_id']}</code>\n"
            text += f"   📅 С: {join_date}\n"

            # Помечаем главного админа
            if admin_dict['user_id'] == 907331808:
                text += f"   👑 <i>Главный администратор</i>\n"

            text += "\n"

        text += f"<b>Всего администраторов:</b> {len(admins)}"

        await update.message.reply_text(text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Ошибка получения списка админов: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка администраторов")