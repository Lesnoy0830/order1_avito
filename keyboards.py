from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, записать меня!")],
            [KeyboardButton(text="❌ Нет, не сейчас")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Список пользователей")],
            [KeyboardButton(text="🔧 Управление пользователями")],
            [KeyboardButton(text="📝 Управление челленджем")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_back_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )
    return keyboard

def get_management_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Забанить", callback_data="admin_ban")],
            [InlineKeyboardButton(text="🔓 Разбанить", callback_data="admin_unban")],
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="admin_block")],
            [InlineKeyboardButton(text="✅ Активировать", callback_data="admin_activate")]
        ]
    )
    return keyboard

def get_challenge_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать новый челлендж", callback_data="create_challenge")],
            [InlineKeyboardButton(text="✏️ Изменить задание", callback_data="update_task")]
        ]
    )
    return keyboard

def get_cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    return keyboard