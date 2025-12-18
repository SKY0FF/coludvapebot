# admin.py - с полным функционалом рассылки
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler, Application
)
import logging
from datetime import datetime
import asyncio
from database import db

logger = logging.getLogger(__name__)

# Константы для состояний
CATEGORY, NAME, PRICE, DESCRIPTION = range(4)

# Список администраторов по умолчанию (добавьте свои ID)
DEFAULT_ADMINS = [907331808, 8296314100]  # Замените на ваш ID

# === ОСНОВНЫЕ ФУНКЦИИ ДОБАВЛЕНИЯ ТОВАРА (ПОСТАВЛЕНЫ В НАЧАЛО) ===

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление нового товара (начало диалога)"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return ConversationHandler.END
    
    # Показываем клавиатуру с категориями
    keyboard = [
        [InlineKeyboardButton("🔋 POD-системы", callback_data='add_pod_systems')],
        [InlineKeyboardButton("💧 Жидкости", callback_data='add_liquids')],
        [InlineKeyboardButton("⚡ Испарители", callback_data='add_coils')],
        [InlineKeyboardButton("🎒 Аксессуары", callback_data='add_accessories')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_add')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите категорию для нового товара:",
        reply_markup=reply_markup
    )
    
    return CATEGORY

async def process_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора категории"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_add':
        await query.edit_message_text("❌ Добавление товара отменено.")
        return ConversationHandler.END
    
    # Сохраняем категорию
    category_map = {
        'add_pod_systems': 'pod_systems',
        'add_liquids': 'liquids',
        'add_coils': 'coils',
        'add_accessories': 'accessories'
    }
    
    context.user_data['new_product_category'] = category_map[query.data]
    
    await query.edit_message_text(
        "📝 Введите название товара:\n\n"
        "<i>Пример: HQD Cuvie Ultra 2500</i>",
        parse_mode='HTML'
    )
    
    return NAME

async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия товара"""
    context.user_data['new_product_name'] = update.message.text
    
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
        context.user_data['new_product_price'] = price
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректную цену (целое число больше 0).")
        return PRICE
    
    await update.message.reply_text(
        "📋 Введите описание товара:\n\n"
        "<i>Пример: 2500 тяг, 20 вкусов, тип: одноразовый</i>",
        parse_mode='HTML'
    )
    
    return DESCRIPTION

async def process_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания товара и сохранение"""
    context.user_data['new_product_description'] = update.message.text
    
    # Здесь в реальном проекте вы бы сохраняли товар в базу данных
    # Для примера просто выводим информацию
    
    product_info = (
        "✅ <b>Товар успешно добавлен!</b>\n\n"
        f"<b>Категория:</b> {context.user_data['new_product_category']}\n"
        f"<b>Название:</b> {context.user_data['new_product_name']}\n"
        f"<b>Цена:</b> {context.user_data['new_product_price']}₽\n"
        f"<b>Описание:</b> {context.user_data['new_product_description']}\n\n"
        "<i>В реальном проекте товар будет сохранен в базу данных</i>"
    )
    
    await update.message.reply_text(product_info, parse_mode='HTML')
    
    # Очищаем временные данные
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления товара"""
    await update.message.reply_text("❌ Добавление товара отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# === ConversationHandler для добавления товара (после определений функций) ===
add_product_handler = ConversationHandler(
    entry_points=[CommandHandler('add_product', add_product)],
    states={
        CATEGORY: [CallbackQueryHandler(process_category)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_name)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_price)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_description)],
    },
    fallbacks=[CommandHandler('cancel', cancel_add)],
)

# === ФУНКЦИИ РАССЫЛКИ И АДМИНКИ (ОСТАЛЬНОЙ КОД) ===

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return
    
    user_count = db.get_user_count()
    active_count = db.get_active_user_count()
    
    text = (
        f"⚙️ <b>Панель администратора VapeShop</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Всего пользователей: {user_count}\n"
        f"• Активных (с уведомлениями): {active_count}\n\n"
        "<b>Команды управления:</b>\n"
        "/add_product - Добавить товар\n"
        "/stats - Подробная статистика\n"
        "<b>/broadcast - Рассылка сообщения</b>\n"
        "/broadcast_history - История рассылок\n"
        "/make_admin [ID] - Назначить админом\n"
        "/user_info [ID] - Инфо о пользователе\n\n"
        "<b>Быстрые действия:</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем", callback_data='admin_broadcast_all')],
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 Управление пользователями", callback_data='admin_users')],
        [InlineKeyboardButton("➕ Добавить товар", callback_data='admin_add_product')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса рассылки"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 <b>Создание рассылки</b>\n\n"
            "Отправьте мне сообщение, которое нужно разослать всем пользователям.\n\n"
            "<b>Формат:</b>\n"
            "/broadcast [ваше сообщение]\n\n"
            "<b>Пример:</b>\n"
            "/broadcast 🔥 Акция! Скидка 20% на все жидкости до конца недели!\n\n"
            "<i>Вы также можете отправить фото/документ с подписью для рассылки</i>",
            parse_mode='HTML'
        )
        return
    
    message_text = ' '.join(context.args)
    await start_broadcast_process(update, context, message_text)

async def start_broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str = None):
    """Запуск процесса подтверждения рассылки"""
    if not message_text and 'broadcast_message' in context.user_data:
        message_text = context.user_data['broadcast_message']
    
    if not message_text:
        await update.message.reply_text("❌ Нет текста для рассылки.")
        return
    
    # Сохраняем сообщение
    context.user_data['broadcast_message'] = message_text
    context.user_data['broadcast_type'] = 'text'
    
    # Получаем статистику пользователей
    total_users = db.get_user_count()
    active_users = db.get_active_user_count()
    
    # Создаем клавиатуру подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Да, разослать", callback_data='confirm_broadcast_yes')],
        [InlineKeyboardButton("✏️ Редактировать", callback_data='edit_broadcast')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_broadcast')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    preview_text = (
        f"📢 <b>Предпросмотр рассылки</b>\n\n"
        f"<b>Сообщение:</b>\n{message_text}\n\n"
        f"<b>Статистика охвата:</b>\n"
        f"• Всего пользователей: {total_users}\n"
        f"• Получат рассылку: {active_users}\n"
        f"• Не получат (отключили уведомления): {total_users - active_users}\n\n"
        f"<i>Подтвердите отправку или отредактируйте сообщение.</i>"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            preview_text, 
            reply_markup=reply_markup, 
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(preview_text, reply_markup=reply_markup, parse_mode='HTML')

async def confirm_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения рассылки через callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm_broadcast_yes':
        await execute_broadcast(update, context)
    elif query.data == 'edit_broadcast':
        await query.edit_message_text(
            "✏️ <b>Редактирование рассылки</b>\n\n"
            "Отправьте мне новый текст сообщения:",
            parse_mode='HTML'
        )
        context.user_data['awaiting_edit'] = True
    elif query.data == 'cancel_broadcast':
        await query.edit_message_text("❌ Рассылка отменена.")
        context.user_data.clear()

async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение рассылки"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        if update.callback_query:
            await update.callback_query.edit_message_text("⛔ У вас нет прав администратора!")
        return
    
    # Получаем данные из контекста
    message_text = context.user_data.get('broadcast_message', '')
    broadcast_type = context.user_data.get('broadcast_type', 'text')
    
    # Получаем пользователей
    users = db.get_all_users(active_only=True)
    total_users = len(users)
    
    if total_users == 0:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Нет активных пользователей для рассылки.")
        return
    
    # Сохраняем информацию о рассылке в БД
    broadcast_id = db.save_broadcast_message(user_id, message_text, total_users)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"🔄 <b>Начинаю рассылку...</b>\n\n"
            f"Получателей: {total_users}\n"
            f"ID рассылки: {broadcast_id}\n\n"
            f"<i>Это может занять некоторое время.</i>",
            parse_mode='HTML'
        )
    
    # Статистика
    sent_count = 0
    failed_count = 0
    
    # Рассылка
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=message_text,
                parse_mode='HTML'
            )
            sent_count += 1
            
            # Небольшая задержка, чтобы не превысить лимиты Telegram
            if sent_count % 20 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ошибка при отправке пользователю {user['user_id']}: {e}")
            failed_count += 1
            
            # Если пользователь заблокировал бота, отключаем уведомления
            if "bot was blocked" in str(e).lower() or "chat not found" in str(e).lower():
                db.disable_user_notifications(user['user_id'])
    
    # Обновляем статус рассылки в БД
    db.update_broadcast_status(broadcast_id, sent_count, failed_count, 'completed')
    
    # Отправляем отчет администратору
    report_text = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"<b>Статистика:</b>\n"
        f"• Всего получателей: {total_users}\n"
        f"• Успешно отправлено: {sent_count}\n"
        f"• Не удалось отправить: {failed_count}\n"
        f"• ID рассылки: {broadcast_id}\n\n"
    )
    
    if failed_count > 0:
        report_text += "<i>Некоторым пользователям не удалось отправить сообщение. Возможно, они заблокировали бота.</i>"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(report_text, parse_mode='HTML')
    else:
        await update.message.reply_text(report_text, parse_mode='HTML')
    
    # Очищаем контекст
    context.user_data.clear()

async def broadcast_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """История рассылок"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return
    
    history = db.get_broadcast_history(limit=10)
    
    if not history:
        await update.message.reply_text("📜 История рассылок пуста.")
        return
    
    text = "<b>📜 История рассылок (последние 10):</b>\n\n"
    
    for item in history:
        try:
            date = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
        except:
            date = item['created_at']
        
        status_emoji = "✅" if item['status'] == 'completed' else "🔄" if item['status'] == 'sending' else "❌"
        
        text += (
            f"{status_emoji} <b>Рассылка #{item['id']}</b>\n"
            f"📅 {date}\n"
            f"👤 Админ: {item['admin_id']}\n"
            f"👥 Получателей: {item['total_users']}\n"
            f"✓ Отправлено: {item['sent_count']}\n"
            f"✗ Ошибок: {item['failed_count']}\n"
            f"📝 {item['message_text'][:50]}...\n"
            f"{'-'*30}\n"
        )
    
    await update.message.reply_text(text, parse_mode='HTML')

async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Назначение администратора"""
    user_id = update.effective_user.id
    
    if user_id not in DEFAULT_ADMINS:
        await update.message.reply_text("⛔ Только главный администратор может назначать других!")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /make_admin [ID_пользователя]")
        return
    
    try:
        new_admin_id = int(context.args[0])
        if db.add_admin(new_admin_id):
            await update.message.reply_text(f"✅ Пользователь {new_admin_id} назначен администратором!")
        else:
            await update.message.reply_text("❌ Ошибка при назначении администратора.")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используйте число.")

async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о пользователе"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return
    
    if not context.args:
        # Информация о себе
        target_id = user_id
    else:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Неверный ID. Используйте число.")
            return
    
    await update.message.reply_text(
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"ID: {target_id}\n"
        f"Статус: {'Администратор' if db.is_admin(target_id) else 'Пользователь'}\n\n"
        f"<i>Для получения полной информации подключите запросы к базе данных.</i>",
        parse_mode='HTML'
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подробная статистика"""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав администратора!")
        return
    
    total_users = db.get_user_count()
    active_users = db.get_active_user_count()
    admins = db.get_admins()
    
    text = (
        f"📊 <b>Детальная статистика</b>\n\n"
        f"<b>Пользователи:</b>\n"
        f"• Всего зарегистрировано: {total_users}\n"
        f"• Активные (с уведомлениями): {active_users}\n"
        f"• Неактивные: {total_users - active_users}\n\n"
        f"<b>Администраторы ({len(admins)}):</b>\n"
    )
    
    for admin_id in admins:
        text += f"• {admin_id}\n"
    
    text += f"\n<b>Рассылки:</b>\n"
    
    history = db.get_broadcast_history(limit=5)
    if history:
        total_sent = sum(item['sent_count'] for item in history)
        total_failed = sum(item['failed_count'] for item in history)
        text += f"• Последних рассылок: {len(history)}\n"
        text += f"• Всего отправлено: {total_sent}\n"
        text += f"• Всего ошибок: {total_failed}\n"
    else:
        text += "• Рассылок еще не было\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

# Обработчик для редактирования сообщения рассылки
async def handle_broadcast_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка редактирования сообщения рассылки"""
    if context.user_data.get('awaiting_edit'):
        new_text = update.message.text
        context.user_data['broadcast_message'] = new_text
        context.user_data['awaiting_edit'] = False
        
        await start_broadcast_process(update, context, new_text)

# Регистрация обработчиков для кнопок админки
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов админки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_broadcast_all':
        await query.edit_message_text(
            "📢 <b>Создание рассылки</b>\n\n"
            "Отправьте мне текст сообщения, которое нужно разослать:",
            parse_mode='HTML'
        )
    elif query.data == 'admin_stats':
        await show_stats(update, context)
    elif query.data == 'admin_users':
        await query.edit_message_text(
            "👥 <b>Управление пользователями</b>\n\n"
            "Доступные команды:\n"
            "/user_info [ID] - Информация о пользователе\n"
            "/make_admin [ID] - Назначить администратором\n\n"
            "Для просмотра статистики используйте /stats",
            parse_mode='HTML'
        )
    elif query.data == 'admin_add_product':
        await add_product(update, context)
