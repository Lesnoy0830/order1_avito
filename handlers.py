from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from constants import USER_ACTIVE, USER_BLOCKED, ADMIN_IDS, CHANNEL_ID
from keyboards import get_start_keyboard, get_admin_keyboard, get_back_keyboard, get_management_keyboard, get_cancel_keyboard, get_challenge_keyboard
from datetime import date, timedelta
import logging

router = Router()
db = Database()

class AdminStates(StatesGroup):
    waiting_for_challenge_name = State()
    waiting_for_challenge_task = State()
    waiting_for_challenge_days = State()
    waiting_for_block_user_id = State()
    waiting_for_activate_user_id = State()
    waiting_for_update_task = State()

# Функция проверки подписки на канал
async def check_channel_subscription(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking channel subscription for {user_id}: {e}")
        return False

# Простой тестовый хендлер для проверки (только для админов)
@router.message(Command("test"))
async def cmd_test(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("✅ Бот работает! Тестовое сообщение получено.")
    else:
        await message.answer("У вас нет доступа к этой команде.")

# Основные хендлеры
@router.message(Command("start"))
async def cmd_start(message: Message):
    logging.info(f"Start command received from user {message.from_user.id}")
    
    user = await db.get_user(message.from_user.id)
    
    if user:
        challenge_info = await db.get_challenge_info()
        user_day = await db.get_user_current_day(message.from_user.id)
        
        if challenge_info:
            if user_day == 0:
                challenge_text = (
                    f"🏆 Предстоящий челлендж: {challenge_info['name']}\n"
                    f"📅 Начало: {challenge_info['start_date']}\n"
                    f"💪 Всего дней: {challenge_info['total_days']}\n\n"
                    f"Челлендж еще не начался! Первый день: {challenge_info['start_date']}"
                )
            else:
                challenge_text = (
                    f"🏆 Активный челлендж: {challenge_info['name']}\n"
                    f"📅 День: {user_day}/{challenge_info['total_days']}\n"
                    f"💪 Задание: {user_day} {challenge_info['task']}\n\n"
                    f"Отправляй кружочек (видео-сообщение), чтобы отметить выполнение задания!"
                )
        else:
            challenge_text = "В настоящее время нет активного челленджа."
        
        await message.answer(
            challenge_text
        )
    else:
        await message.answer(
            "Привет! Записывать тебя в участники?",
            reply_markup=get_start_keyboard()
        )

@router.message(F.text == "✅ Да, записать меня!")
async def agree_participation(message: Message):
    # Проверяем подписку на канал
    is_subscribed = await check_channel_subscription(message.bot, message.from_user.id)
    
    if not is_subscribed:
        await message.answer(
            "📢 Для участия в челлендже необходимо подписаться на наш канал!\n\n"
            f"Подпишитесь на канал @do_push", #
            reply_markup=get_start_keyboard() if message.from_user.id in ADMIN_IDS else None
        )
        return
    
    # Если подписан - продолжаем запись
    await db.add_user(message.from_user.id, message.from_user.username)
    challenge_info = await db.get_challenge_info()
    
    if challenge_info:
        user_day = await db.get_user_current_day(message.from_user.id)
        if user_day == 0:
            challenge_text = (
                f"🎉 Отлично! Ты записан в челлендж: {challenge_info['name']}\n\n"
                f"📅 Начало: {challenge_info['start_date']}\n"
                f"💪 Всего дней: {challenge_info['total_days']}\n\n"
                f"Челлендж еще не начался! Первый день: {challenge_info['start_date']}"
            )
        else:
            challenge_text = (
                f"🎉 Отлично! Ты записан в челлендж: {challenge_info['name']}\n\n"
                f"📅 Твой текущий день: {user_day}/{challenge_info['total_days']}\n"
                f"💪 Сегодня нужно сделать: {user_day} {challenge_info['task']}\n\n"
                f"Каждый день отправляй кружочек (видео-сообщение), чтобы отметить выполнение задания. "
                f"Напоминания будут приходить в 7:00, 15:00 и 19:00 по МСК.\n"
                f"Счетчик напоминаний сбрасывается каждый день в 00:00!"
            )
    else:
        challenge_text = "Ты записан, но в настоящее время нет активного челленджа."
    
    await message.answer(
        challenge_text,
        reply_markup=get_back_keyboard() if message.from_user.id in ADMIN_IDS else None
    )

@router.message(F.text == "❌ Нет, не сейчас")
async def decline_participation(message: Message):
    await message.answer(
        "Хорошо, если передумаешь - просто нажми /start снова!",
        reply_markup=get_back_keyboard() if message.from_user.id in ADMIN_IDS else None
    )

@router.message(F.video_note)
async def handle_video_note(message: Message):
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("Сначала нужно зарегистрироваться через /start")
        return
    
    user_status = user[2]  # status field
    
    if user_status == USER_BLOCKED:
        await message.answer("Вы заблокированы. Обратитесь к администратору для разблокировки.")
        return
    
    # Получаем текущий день пользователя
    user_day = await db.get_user_current_day(message.from_user.id)
    challenge_info = await db.get_challenge_info()
    
    if user_day == 0:
        await message.answer("Челлендж еще не начался!")
        return
    
    today = date.today()
    last_completion = user[3]  # last_completion_date field
    
    if last_completion and last_completion == today.isoformat():
        await message.answer("Вы уже выполнили задание на сегодня!")
        return
    
    # Обновляем выполнение задания
    await db.update_user_completion(message.from_user.id, today)
    
    # Отправляем в канал
    if challenge_info:
        channel_message = (
            f"🎉 Пользователь: @{message.from_user.username or 'без username'} "
            f"выполнил {user_day}-й день челленджа '{challenge_info['name']}'!\n"
            f"💪 Сделано: {user_day} {challenge_info['task']}"
        )
    else:
        channel_message = f"Пользователь: @{message.from_user.username or 'без username'} выполнил сегодняшний челлендж!"
    
    try:
        # Отправляем видео-кружочек в канал
        await message.bot.send_video_note(
            CHANNEL_ID, 
            message.video_note.file_id
        )
        # Отправляем отдельное сообщение с информацией о пользователе
        await message.bot.send_message(
            CHANNEL_ID,
            channel_message
        )
        
        # Сообщение пользователю
        if challenge_info:
            await message.answer(
                f"🎉 Отлично! Ты выполнил {user_day}-й день челленджа!\n"
                f"💪 Ты сделал(а) {user_day} {challenge_info['task']}!\n"
                f"📹 Твой кружочек отправлен в канал."
            )
        else:
            await message.answer("Отлично! Ты выполнил задание на сегодня! 🎉 Твой кружочек отправлен в канал.")
            
    except Exception as e:
        logging.error(f"Failed to send video note to channel: {e}")
        await message.answer("Отлично! Ты выполнил задание на сегодня! 🎉 (Ошибка отправки в канал)")

# Админ панель
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к админ панели.")
        return
    
    await message.answer("Админ панель", reply_markup=get_admin_keyboard())

@router.message(F.text == "⬅️ Назад")
async def back_to_admin(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Админ панель", reply_markup=get_admin_keyboard())

@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_admin_keyboard())

# Управление челленджем
@router.message(F.text == "📝 Управление челленджем")
async def manage_challenge(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    challenge_info = await db.get_challenge_info()
    if challenge_info:
        challenge_text = (
            f"Текущий челлендж:\n"
            f"🏆 Название: {challenge_info['name']}\n"
            f"💪 Задание: {challenge_info['task']}\n"
            f"📅 Всего дней: {challenge_info['total_days']}\n"
            f"📅 Начало: {challenge_info['start_date']}\n"
            f"📅 Текущий день: {challenge_info['current_day']}"
        )
    else:
        challenge_text = "Активный челлендж не установлен"
    
    await message.answer(challenge_text, reply_markup=get_challenge_keyboard())

@router.callback_query(F.data == "create_challenge")
async def create_challenge_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название нового челленджа:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_challenge_name)
    await callback.answer()

@router.callback_query(F.data == "update_task")
async def update_task_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое задание для челленджа (например: 'отжиманий', 'приседаний', 'подтягиваний'):", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_update_task)
    await callback.answer()

@router.message(AdminStates.waiting_for_challenge_name)
async def process_challenge_name(message: Message, state: FSMContext):
    await state.update_data(challenge_name=message.text)
    await message.answer("Введите задание для челленджа (например: 'отжиманий', 'приседаний', 'подтягиваний'):", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_challenge_task)

@router.message(AdminStates.waiting_for_challenge_task)
async def process_challenge_task(message: Message, state: FSMContext):
    await state.update_data(challenge_task=message.text)
    await message.answer("Введите количество дней для челленджа:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_challenge_days)

@router.message(AdminStates.waiting_for_challenge_days)
async def process_challenge_days(message: Message, state: FSMContext):
    try:
        days = int(message.text)
        if days <= 0:
            await message.answer("Количество дней должно быть положительным числом. Попробуйте снова:")
            return
        
        data = await state.get_data()
        challenge_name = data.get('challenge_name')
        challenge_task = data.get('challenge_task')
        
        await db.set_challenge(challenge_name, challenge_task, days)
        await message.answer(
            f"✅ Новый челлендж создан!\n"
            f"🏆 Название: {challenge_name}\n"
            f"💪 Задание: {challenge_task}\n"
            f"📅 Дней: {days}\n"
            f"📅 Начало: {date.today() + timedelta(days=1)}\n"
            f"🔄 Все пользователи начинают с 1 дня",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("Неверный формат. Введите число дней:")

@router.message(AdminStates.waiting_for_update_task)
async def process_update_task(message: Message, state: FSMContext):
    await db.update_challenge_task(message.text)
    await message.answer(
        f"✅ Задание челленджа обновлено!\n"
        f"💪 Новое задание: {message.text}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# Управление пользователями
@router.message(F.text == "🔧 Управление пользователями")
async def manage_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("Выберите действие:", reply_markup=get_management_keyboard())

# Callback хендлеры для управления пользователями
@router.callback_query(F.data.startswith("admin_"))
async def admin_management_callback(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    
    actions = {
        "block": ("блокировки", AdminStates.waiting_for_block_user_id, USER_BLOCKED),
        "activate": ("активации", AdminStates.waiting_for_activate_user_id, USER_ACTIVE)
    }
    
    if action in actions:
        text, state_name, status = actions[action]
        await callback.message.answer(f"Введите ID пользователя для {text}:", reply_markup=get_cancel_keyboard())
        await state.set_state(state_name)
        await state.update_data(action_status=status)
    
    await callback.answer()

# Обработчики для разных действий
@router.message(AdminStates.waiting_for_block_user_id)
@router.message(AdminStates.waiting_for_activate_user_id)
async def process_user_management(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user_data = await state.get_data()
        action_status = user_data.get('action_status', USER_ACTIVE)
        
        # Проверяем существование пользователя
        user = await db.get_user(user_id)
        if not user:
            await message.answer("Пользователь с таким ID не найден.", reply_markup=get_admin_keyboard())
            await state.clear()
            return
        
        # Обновляем статус
        await db.update_user_status(user_id, action_status)
        
        status_names = {
            USER_BLOCKED: "заблокирован", 
            USER_ACTIVE: "активирован (счетчик напоминаний сброшен)"
        }
        
        await message.answer(
            f"Пользователь {user_id} {status_names[action_status]}.",
            reply_markup=get_admin_keyboard()
        )
        
    except ValueError:
        await message.answer("Неверный формат ID. Введите числовой ID.", reply_markup=get_cancel_keyboard())
        return
    
    await state.clear()

# Список пользователей
@router.message(F.text == "👥 Список пользователей")
async def list_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users = await db.get_all_users()
    if not users:
        await message.answer("Нет пользователей.")
        return
    
    users_list = []
    for user in users:
        status_emoji = {
            USER_ACTIVE: "✅",
            USER_BLOCKED: "🚫"
        }.get(user[2], "❓")
        
        users_list.append(f"{status_emoji} ID: {user[0]}, Username: @{user[1] or 'нет'}, Статус: {user[2]}, День: {user[4]}, Напоминаний: {user[3]}")
    
    # Разбиваем на части если сообщение слишком длинное
    message_text = "Все пользователи:\n" + "\n".join(users_list)
    if len(message_text) > 4096:
        parts = [message_text[i:i+4096] for i in range(0, len(message_text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(message_text)

# Статистика
@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users = await db.get_all_users()
    completed_today = await db.get_users_without_today_completion()
    challenge_info = await db.get_challenge_info()
    
    active_users = [u for u in users if u[2] == USER_ACTIVE]
    blocked_users = [u for u in users if u[2] == USER_BLOCKED]
    
    users_with_reminders = [u for u in users if u[3] > 0]  # users with reminder_count > 0
    
    stats_text = (
        f"📊 Статистика:\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"✅ Активных: {len(active_users)}\n"
        f"🚫 Заблокированных: {len(blocked_users)}\n"
        f"📅 Выполнили сегодня: {len(active_users) - len(completed_today)}\n"
        f"⏰ Не выполнили сегодня: {len(completed_today)}\n"
        f"🔔 Пользователей с напоминаниями: {len(users_with_reminders)}"
    )
    
    if challenge_info:
        stats_text += f"\n\n🏆 Текущий челлендж: {challenge_info['name']}\n"
        stats_text += f"💪 Задание: {challenge_info['task']}\n"
        stats_text += f"📅 Всего дней: {challenge_info['total_days']}\n"
        stats_text += f"📅 Начало: {challenge_info['start_date']}\n"
        stats_text += f"📅 Текущий день: {challenge_info['current_day']}"
    
    await message.answer(stats_text)
