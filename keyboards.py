from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import MATERIALS_CHANNEL, STARTER_PACK_LINK, INFO_LINK, SUPPORT_LINK

def get_main_keyboard(is_admin=False):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Личный кабинет")],
            [KeyboardButton(text="🤝 Сотрудничество")],
            [KeyboardButton(text="💬 Связь с поддержкой")]
        ],
        resize_keyboard=True
    )
    
    if is_admin:
        keyboard.keyboard.append([KeyboardButton(text="👑 Админ панель")])
    
    return keyboard

def get_lk_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )

def get_cooperation_unregistered_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Пройти тест", callback_data="start_test")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )

def get_cooperation_after_test_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="create_promo")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )

def get_cooperation_registered_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Статья", callback_data="article")],
            [InlineKeyboardButton(text="📚 Материалы", callback_data="materials")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )

def get_test_keyboard(question_num, question_data):
    if question_num == 0:
        return None
    
    buttons = []
    for i in range(len(question_data['options'])):
        buttons.append([InlineKeyboardButton(text=question_data['options'][i], callback_data=f"answer_{i}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Таблица партнеров", callback_data="partners_table")],
            [InlineKeyboardButton(text="🔍 Поиск партнера", callback_data="search_partner")],
            [InlineKeyboardButton(text="📊 Лог выплат", callback_data="withdrawal_log")],
            [InlineKeyboardButton(text="📥 Экспорт данных", callback_data="export_data")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )

def get_partner_actions_keyboard(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ 1 реферал", callback_data=f"add_ref_{user_id}")],
            [InlineKeyboardButton(text="➕ 500 руб.", callback_data=f"add_balance_{user_id}")],
            [InlineKeyboardButton(text="✏️ Изменить вручную", callback_data=f"edit_manual_{user_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
        ]
    )

def get_withdrawal_actions_keyboard(withdrawal_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"complete_withdrawal_{withdrawal_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdrawal_{withdrawal_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
        ]
    )

def get_cancel_reject_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить отклонение", callback_data="cancel_reject")]
        ]
    )

def get_article_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎒 STARTER PACK", url=STARTER_PACK_LINK)],
            [InlineKeyboardButton(text="📋 Прикладная информация", url=INFO_LINK)],
            [InlineKeyboardButton(text="💬 Поддержка", url=f"https://t.me/{SUPPORT_LINK}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_cooperation")]
        ]
    )

def get_materials_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Канал с материалами", url=MATERIALS_CHANNEL)],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_cooperation")]
        ]
    )

def get_back_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ]
    )