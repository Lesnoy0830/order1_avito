import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
CHANNEL_ID = os.getenv('CHANNEL_ID')

# Название челленджа по умолчанию
DEFAULT_CHALLENGE_NAME = "Челлендж 75 дней"
DEFAULT_CHALLENGE_DAYS = 75

# Время обновления задания (00:00 по МСК)
UPDATE_HOUR = 0
UPDATE_MINUTE = 0

# Время напоминаний (7:30 и 15:00 по МСК)
REMINDER_TIMES = [(7, 30), (15, 0)]

# Интервал между напоминаниями (в часах) - для логики блокировки
REMINDER_INTERVAL_HOURS = 7.5

# Состояния пользователя
USER_ACTIVE = "active"
USER_BLOCKED = "blocked"
USER_BANNED = "banned"
