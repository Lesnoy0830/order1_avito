import aiosqlite
import asyncio
from datetime import datetime, date, timedelta
from constants import USER_ACTIVE, USER_BLOCKED, USER_BANNED

class Database:
    def __init__(self, db_path='bot.db'):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    status TEXT DEFAULT 'active',
                    last_completion_date DATE,
                    reminder_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    start_date DATE,
                    current_day INTEGER DEFAULT 0,
                    last_reminder_time TIMESTAMP  -- ДОБАВИТЬ ЭТУ СТРОЧКУ
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admin_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS challenge_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenge_name TEXT,
                    challenge_task TEXT,
                    total_days INTEGER,
                    start_date DATE,
                    current_day INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            await db.commit()

    async def add_user(self, telegram_id: int, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем текущий активный челлендж
            current_challenge = await self.get_current_challenge()
            start_date = date.today() if current_challenge else None
            
            await db.execute(
                'INSERT OR IGNORE INTO users (telegram_id, username, start_date, current_day) VALUES (?, ?, ?, ?)',
                (telegram_id, username, start_date, 1)
            )
            await db.commit()

    async def get_user(self, telegram_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM users WHERE telegram_id = ?', 
                (telegram_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def update_user_completion(self, telegram_id: int, completion_date: date):
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем текущий день челленджа для пользователя
            user = await self.get_user(telegram_id)
            if user and user[6]:  # start_date
                start_date = datetime.strptime(user[6], '%Y-%m-%d').date()
                current_day = (completion_date - start_date).days + 1
                
                await db.execute(
                    'UPDATE users SET last_completion_date = ?, reminder_count = 0, current_day = ? WHERE telegram_id = ?',
                    (completion_date, current_day, telegram_id)
                )
            else:
                await db.execute(
                    'UPDATE users SET last_completion_date = ?, reminder_count = 0 WHERE telegram_id = ?',
                    (completion_date, telegram_id)
                )
            await db.commit()

    async def reset_daily_completions(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Сбрасываем только last_completion_date, НЕ сбрасываем reminder_count
            await db.execute('UPDATE users SET last_completion_date = NULL')
            await db.commit()

    async def get_all_active_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT telegram_id, username FROM users WHERE status = ?', 
                (USER_ACTIVE,)
            ) as cursor:
                return await cursor.fetchall()

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT telegram_id, username, status, reminder_count, current_day FROM users'
            ) as cursor:
                return await cursor.fetchall()

    async def get_users_without_today_completion(self):
        today = date.today()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT telegram_id, username, reminder_count, current_day FROM users 
                WHERE (last_completion_date != ? OR last_completion_date IS NULL) 
                AND status = ?''',
                (today, USER_ACTIVE)
            ) as cursor:
                return await cursor.fetchall()

    async def update_user_status(self, telegram_id: int, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            # Сбрасываем счетчик напоминаний только при активации
            if status == USER_ACTIVE:
                await db.execute(
                    'UPDATE users SET status = ?, reminder_count = 0 WHERE telegram_id = ?',
                    (status, telegram_id)
                )
            else:
                await db.execute(
                    'UPDATE users SET status = ? WHERE telegram_id = ?',
                    (status, telegram_id)
                )
            await db.commit()

    async def increment_reminder_count(self, telegram_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET reminder_count = reminder_count + 1 WHERE telegram_id = ?',
                (telegram_id,)
            )
            await db.commit()

    async def get_reminder_count(self, telegram_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT reminder_count FROM users WHERE telegram_id = ?', 
                (telegram_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def reset_reminder_count(self, telegram_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET reminder_count = 0 WHERE telegram_id = ?',
                (telegram_id,)
            )
            await db.commit()

    # Методы для управления челленджем
    async def set_challenge(self, name: str, task: str, days: int):
        async with aiosqlite.connect(self.db_path) as db:
            # Деактивируем предыдущие челленджи
            await db.execute('UPDATE challenge_progress SET is_active = FALSE')
            
            # Создаем новый челлендж
            await db.execute(
                'INSERT INTO challenge_progress (challenge_name, challenge_task, total_days, start_date, current_day, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                (name, task, days, date.today(), 1, True)
            )
            
            # Сбрасываем прогресс всех пользователей
            await db.execute('UPDATE users SET start_date = ?, current_day = 1, reminder_count = 0', (date.today(),))
            
            await db.commit()

    async def get_current_challenge(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT challenge_name, challenge_task, total_days, start_date, current_day FROM challenge_progress WHERE is_active = TRUE ORDER BY id DESC LIMIT 1'
            ) as cursor:
                return await cursor.fetchone()

    async def increment_challenge_day(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE challenge_progress SET current_day = current_day + 1 WHERE is_active = TRUE'
            )
            await db.commit()

    async def get_user_current_day(self, telegram_id: int):
        user = await self.get_user(telegram_id)
        if user and user[7]:  # current_day
            return user[7]
        return 1

    async def get_challenge_info(self):
        challenge = await self.get_current_challenge()
        if challenge:
            name, task, total_days, start_date, current_day = challenge
            return {
                'name': name,
                'task': task,
                'total_days': total_days,
                'start_date': start_date,
                'current_day': current_day
            }
        return None

    async def update_challenge_task(self, task: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE challenge_progress SET challenge_task = ? WHERE is_active = TRUE',
                (task,)
            )
            await db.commit()
    
    async def update_last_reminder_time(self, telegram_id: int, reminder_time: datetime):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET last_reminder_time = ? WHERE telegram_id = ?',
                (reminder_time, telegram_id)
            )
            await db.commit()

    async def get_last_reminder_time(self, telegram_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT last_reminder_time FROM users WHERE telegram_id = ?', 
                (telegram_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result and result[0]:
                    return datetime.fromisoformat(result[0])
                return None

    async def increment_reminder_count(self, telegram_id: int, reminder_time: datetime = None):
        async with aiosqlite.connect(self.db_path) as db:
            if reminder_time:
                await db.execute(
                    'UPDATE users SET reminder_count = reminder_count + 1, last_reminder_time = ? WHERE telegram_id = ?',
                    (reminder_time, telegram_id)
                )
            else:
                await db.execute(
                    'UPDATE users SET reminder_count = reminder_count + 1 WHERE telegram_id = ?',
                    (telegram_id,)
                )
            await db.commit()