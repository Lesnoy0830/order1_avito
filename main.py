import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time
import pytz

from handlers import router
from database import Database
from constants import BOT_TOKEN, REMINDER_INTERVAL_HOURS, USER_BLOCKED, UPDATE_HOUR, UPDATE_MINUTE, REMINDER_TIMES
from keyboards import get_back_keyboard

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    db = Database()
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    
    # Инициализация БД
    await db.init_db()
    logging.info("Database initialized")
    
    # Регистрация роутеров
    dp.include_router(router)
    
    # Функция для ежедневного сброса и увеличения дня челленджа
    async def reset_daily_tasks():
        await db.reset_daily_completions()
        await db.increment_challenge_day()
        logging.info("Daily tasks reset and challenge day incremented at 00:00")
    
    # Функция для напоминаний (только для активных пользователей)
    async def send_reminders():
        users = await db.get_users_without_today_completion()
        challenge_info = await db.get_challenge_info()
        logging.info(f"Sending reminders to {len(users)} users")
        
        blocked_users_count = 0
        current_time = datetime.now()
        
        for user in users:
            try:
                telegram_id, username, reminder_count, current_day = user
                
                # Проверяем интервал между напоминаниями
                should_block = False
                if reminder_count >= 1:
                    # Если это уже не первое напоминание, проверяем интервал
                    last_reminder = await db.get_last_reminder_time(telegram_id)
                    if last_reminder:
                        time_diff = (current_time - last_reminder).total_seconds() / 3600  # в часах
                        if time_diff >= REMINDER_INTERVAL_HOURS:
                            should_block = True
                
                # Увеличиваем счетчик напоминаний и обновляем время
                await db.increment_reminder_count(telegram_id, current_time)
                current_count = await db.get_reminder_count(telegram_id)
                
                logging.info(f"User {telegram_id} has {current_count} reminders (was {reminder_count})")
                
                if should_block:  # Блокировка только если прошел достаточный интервал
                    await db.update_user_status(telegram_id, USER_BLOCKED)
                    await bot.send_message(
                        telegram_id,
                        "❌ Вы заблокированы за невыполнение задания! Обратитесь к администратору для разблокировки."
                    )
                    blocked_users_count += 1
                    logging.info(f"User {telegram_id} blocked after {current_count} reminders with proper interval")
                else:
                    # Отправляем обычное напоминание
                    if challenge_info:
                        reminder_text = (
                            f"🔔 Напоминание #{current_count}!\n"
                            f"🏆 Челлендж: {challenge_info['name']}\n"
                            f"📅 День: {current_day}/{challenge_info['total_days']}\n"
                            f"💪 Сегодня нужно сделать: {current_day} {challenge_info['task']}\n\n"
                            f"Отправь кружочек (видео-сообщение), чтобы отметить выполнение задания!\n"
                            f"Осталось напоминаний до блокировки: {2 - current_count}"
                        )
                    else:
                        reminder_text = (
                            f"🔔 Напоминание #{current_count}! Не забудь выполнить ежедневный челлендж!\n"
                            f"Отправь кружочек (видео-сообщение), чтобы отметить выполнение задания!\n"
                            f"Осталось напоминаний до блокировки: {2 - current_count}"
                        )
                    
                    await bot.send_message(
                        telegram_id,
                        reminder_text,
                        reply_markup=get_back_keyboard()
                    )
                    logging.info(f"Reminder #{current_count} sent to user {telegram_id}")
                    
            except Exception as e:
                logging.error(f"Failed to send reminder to {user[0]}: {e}")
        
        if blocked_users_count > 0:
            logging.info(f"Blocked {blocked_users_count} users for not completing challenge")
    
    # Настройка расписания
    # Ежедневный сброс в 00:00
    scheduler.add_job(reset_daily_tasks, 'cron', hour=UPDATE_HOUR, minute=UPDATE_MINUTE)
    
    # Напоминания в 7:30 и 15:00
    for reminder_time in REMINDER_TIMES:
        hour, minute = reminder_time
        scheduler.add_job(send_reminders, 'cron', hour=hour, minute=minute)
    
    # Запуск планировщика
    scheduler.start()
    logging.info("Scheduler started")
    
    # Установка команд бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="admin", description="Админ панель")
    ])
    
    logging.info("Bot started")
    
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())