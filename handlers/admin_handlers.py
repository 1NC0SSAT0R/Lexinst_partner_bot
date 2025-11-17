import csv
import io
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import Database
from keyboards import *

router = Router()
db = Database()

class SearchStates(StatesGroup):
    waiting_for_search = State()

class EditStates(StatesGroup):
    waiting_for_referrals = State()
    waiting_for_balance = State()

class RejectWithdrawalStates(StatesGroup):
    waiting_for_reason = State()

async def notify_partner(bot, user_id, message_text):
    """Функция для уведомления партнера"""
    try:
        await bot.send_message(user_id, message_text)
    except Exception as e:
        print(f"Failed to notify partner {user_id}: {e}")

@router.message(F.text == "👑 Админ панель")
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Доступ запрещен")
        return
    
    await message.answer(
        "👑 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )

@router.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Доступ запрещен")
        return
    
    await message.answer(
        "👑 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "partners_table")
async def show_partners_table(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    partners = db.get_all_partners()
    
    if not partners:
        await callback.message.edit_text("Партнеры не найдены", reply_markup=get_admin_keyboard())
        return
    
    text = "📋 Таблица партнеров:\n\n"
    for partner in partners[:10]:
        text += f"👤 {partner['full_name']}\n"
        text += f"ID: {partner['user_id']} | @{partner['username'] or 'нет'}\n"
        text += f"🎁 Промокод: {partner['promo_code'] or 'нет'}\n"
        text += f"👥 Рефералов: {partner['referrals']} | 💰 Баланс: {partner['balance']} руб.\n"
        registered_date = partner['registered_at'].split(' ')[0] if isinstance(partner['registered_at'], str) else partner['registered_at']
        text += f"📅 {registered_date}\n"
        text += "─" * 30 + "\n"
    
    if len(partners) > 10:
        text += f"\n... и еще {len(partners) - 10} партнеров"
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "search_partner")
async def search_partner_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    await state.set_state(SearchStates.waiting_for_search)
    await callback.message.edit_text(
        "🔍 Поиск партнера\n\n"
        "Введите ID, username или промокод партнера:",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()

@router.message(SearchStates.waiting_for_search)
async def process_search(message: Message, state: FSMContext):
    search_term = message.text.strip()
    partners = db.search_partners(search_term)
    
    if not partners:
        await message.answer("Партнеры не найдены", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    if len(partners) == 1:
        partner = partners[0]
        
        text = (
            f"👤 Найден партнер:\n\n"
            f"Имя: {partner['full_name']}\n"
            f"ID: {partner['user_id']}\n"
            f"Username: @{partner['username'] or 'нет'}\n"
            f"Промокод: {partner['promo_code'] or 'нет'}\n"
            f"Рефералов: {partner['referrals']}\n"
            f"Баланс: {partner['balance']} руб.\n"
            f"Статус: {'Активен' if partner['is_active'] else 'Не активен'}\n"
        )
        
        if isinstance(partner['registered_at'], str):
            text += f"Регистрация: {partner['registered_at'].split(' ')[0]}"
        else:
            text += f"Регистрация: {partner['registered_at']}"
        
        await message.answer(text, reply_markup=get_partner_actions_keyboard(partner['user_id']))
    else:
        text = "🔍 Найдено несколько партнеров:\n\n"
        for partner in partners[:5]:
            text += f"👤 {partner['full_name']} (ID: {partner['user_id']})\n"
            text += f"   @{partner['username'] or 'нет'} | 🎁 {partner['promo_code'] or 'нет'}\n"
            text += f"   👥 {partner['referrals']} | 💰 {partner['balance']} руб.\n\n"
        
        if len(partners) > 5:
            text += f"... и еще {len(partners) - 5} партнеров"
        
        await message.answer(text, reply_markup=get_admin_keyboard())
    
    await state.clear()

@router.callback_query(F.data.startswith("add_ref_"))
async def add_referral(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    # Получаем текущие данные до изменения
    partner_before = db.get_partner(user_id)
    old_referrals = partner_before['referrals'] if partner_before else 0
    
    db.update_partner_stats(user_id, referrals_delta=1)
    
    partner = db.get_partner(user_id)
    if partner:
        # Уведомляем партнера
        await notify_partner(
            callback.bot,
            user_id,
            f"🎉 Вам начислен +1 реферал!\n\n"
            f"📊 Ваша статистика обновлена:\n"
            f"👥 Было: {old_referrals} рефералов\n"
            f"👥 Стало: {partner['referrals']} рефералов\n"
            f"💰 Текущий баланс: {partner['balance']} руб.\n\n"
            f"Продолжайте в том же духе! 💪"
        )
        
        await callback.message.edit_text(
            f"✅ +1 реферал добавлен!\n\n"
            f"👤 {partner['full_name']}\n"
            f"Рефералов: {partner['referrals']}\n"
            f"Баланс: {partner['balance']} руб.",
            reply_markup=get_partner_actions_keyboard(user_id)
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("add_balance_"))
async def add_balance(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    # Получаем текущие данные до изменения
    partner_before = db.get_partner(user_id)
    old_balance = partner_before['balance'] if partner_before else 0
    
    db.update_partner_stats(user_id, balance_delta=500)
    
    partner = db.get_partner(user_id)
    if partner:
        # Уведомляем партнера
        await notify_partner(
            callback.bot,
            user_id,
            f"💰 Вам начислено +500 рублей!\n\n"
            f"📊 Ваша статистика обновлена:\n"
            f"💰 Было: {old_balance} руб.\n"
            f"💰 Стало: {partner['balance']} руб.\n"
            f"👥 Текущие рефералы: {partner['referrals']}\n\n"
            f"Спасибо за вашу работу! 🚀"
        )
        
        await callback.message.edit_text(
            f"✅ +500 руб. добавлено!\n\n"
            f"👤 {partner['full_name']}\n"
            f"Рефералов: {partner['referrals']}\n"
            f"Баланс: {partner['balance']} руб.",
            reply_markup=get_partner_actions_keyboard(user_id)
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("edit_manual_"))
async def edit_manual_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    # Получаем текущие данные до изменения
    partner_before = db.get_partner(user_id)
    await state.update_data(
        editing_user_id=user_id,
        old_referrals=partner_before['referrals'] if partner_before else 0,
        old_balance=partner_before['balance'] if partner_before else 0
    )
    
    await state.set_state(EditStates.waiting_for_referrals)
    
    await callback.message.edit_text(
        "✏️ Редактирование вручную\n\n"
        "Введите количество рефералов:",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()

@router.message(EditStates.waiting_for_referrals)
async def process_referrals_edit(message: Message, state: FSMContext):
    try:
        referrals = int(message.text)
        data = await state.get_data()
        user_id = data['editing_user_id']
        
        await state.update_data(new_referrals=referrals)
        await state.set_state(EditStates.waiting_for_balance)
        
        await message.answer("Введите баланс:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число:")

@router.message(EditStates.waiting_for_balance)
async def process_balance_edit(message: Message, state: FSMContext):
    try:
        balance = float(message.text)
        data = await state.get_data()
        user_id = data['editing_user_id']
        referrals = data['new_referrals']
        old_referrals = data['old_referrals']
        old_balance = data['old_balance']
        
        db.set_partner_stats(user_id, referrals, balance)
        
        partner = db.get_partner(user_id)
        if partner:
            # Уведомляем партнера об изменениях
            notification_text = "📊 Ваша статистика была обновлена администратором:\n\n"
            
            if old_referrals != referrals:
                notification_text += f"👥 Рефералы:\n"
                notification_text += f"   Было: {old_referrals}\n"
                notification_text += f"   Стало: {referrals}\n"
                notification_text += f"   Изменение: {referrals - old_referrals:+}\n\n"
            
            if old_balance != balance:
                notification_text += f"💰 Баланс:\n"
                notification_text += f"   Было: {old_balance} руб.\n"
                notification_text += f"   Стало: {balance} руб.\n"
                notification_text += f"   Изменение: {balance - old_balance:+.2f} руб.\n\n"
            
            notification_text += "Если у вас есть вопросы, обращайтесь в поддержку."
            
            await notify_partner(message.bot, user_id, notification_text)
            
            await message.answer(
                f"✅ Данные обновлены!\n\n"
                f"👤 {partner['full_name']}\n"
                f"Рефералов: {partner['referrals']}\n"
                f"Баланс: {partner['balance']} руб.",
                reply_markup=get_partner_actions_keyboard(user_id)
            )
        
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.callback_query(F.data == "withdrawal_log")
async def show_withdrawal_log(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    withdrawals = db.get_pending_withdrawals()
    
    if not withdrawals:
        await callback.message.edit_text("Нет pending заявок на вывод", reply_markup=get_admin_keyboard())
        return
    
    text = "📊 Лог выплат (pending):\n\n"
    for withdrawal in withdrawals[:5]:
        text += f"🆔 Заявка #{withdrawal['id']}\n"
        text += f"👤 {withdrawal['full_name']} (@{withdrawal['username'] or 'нет'})\n"
        text += f"💰 Сумма: {withdrawal['amount']} руб.\n"
        text += f"💳 Реквизиты: {withdrawal['requisites'][:20]}...\n"
        
        if isinstance(withdrawal['created_at'], str):
            text += f"📅 Дата: {withdrawal['created_at']}\n"
        else:
            text += f"📅 Дата: {withdrawal['created_at']}\n"
        
        if withdrawal['comment']:
            text += f"💬 Комментарий: {withdrawal['comment']}\n"
        
        text += "─" * 30 + "\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("complete_withdrawal_"))
async def complete_withdrawal(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    withdrawal_id = int(callback.data.split("_")[2])
    success = db.complete_withdrawal(withdrawal_id)
    
    if success:
        # Получаем информацию о заявке для уведомления партнеру
        withdrawal_info = db.get_withdrawal_by_id(withdrawal_id)
        
        if withdrawal_info:
            # Уведомляем партнера
            try:
                await callback.bot.send_message(
                    withdrawal_info['user_id'],
                    f"✅ Ваша заявка на вывод #{withdrawal_id} выполнена!\n\n"
                    f"💸 Сумма: {withdrawal_info['amount']} руб.\n"
                    f"📋 Реквизиты: {withdrawal_info['requisites']}\n"
                    f"⏰ Дата выполнения: {withdrawal_info['processed_at'] or 'только что'}\n\n"
                    f"Средства были переведены на указанные реквизиты.\n"
                    f"Если у вас есть вопросы, обращайтесь в поддержку."
                )
            except Exception as e:
                print(f"Failed to notify partner {withdrawal_info['user_id']}: {e}")
        
        await callback.message.edit_text(
            f"✅ Выплата #{withdrawal_id} выполнена! Партнер уведомлен.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при выполнении выплаты",
            reply_markup=get_admin_keyboard()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("reject_withdrawal_"))
async def reject_withdrawal_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    withdrawal_id = int(callback.data.split("_")[2])
    
    await state.set_state(RejectWithdrawalStates.waiting_for_reason)
    await state.update_data(withdrawal_id=withdrawal_id)
    
    await callback.message.edit_text(
        f"❌ Отклонение заявки #{withdrawal_id}\n\n"
        f"Введите причину отказа (это сообщение увидит партнер):",
        reply_markup=get_cancel_reject_keyboard()
    )
    await callback.answer()

@router.message(RejectWithdrawalStates.waiting_for_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    withdrawal_id = data['withdrawal_id']
    reject_reason = message.text
    
    # Обновляем статус заявки в базе
    success = db.reject_withdrawal(withdrawal_id, reject_reason)
    
    if success:
        # Получаем информацию о заявке
        withdrawal_info = db.get_withdrawal_by_id(withdrawal_id)
        
        if withdrawal_info:
            # Уведомляем партнера об отказе
            try:
                await message.bot.send_message(
                    withdrawal_info['user_id'],
                    f"❌ Ваша заявка на вывод #{withdrawal_id} отклонена.\n\n"
                    f"💸 Сумма: {withdrawal_info['amount']} руб.\n"
                    f"📋 Реквизиты: {withdrawal_info['requisites']}\n"
                    f"📝 Причина отказа: {reject_reason}\n\n"
                    f"Если у вас есть вопросы, обращайтесь в поддержку."
                )
            except Exception as e:
                print(f"Failed to notify partner {withdrawal_info['user_id']}: {e}")
        
        await message.answer(
            f"❌ Заявка #{withdrawal_id} отклонена! Партнер уведомлен о причине.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при отклонении заявки",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "cancel_reject")
async def cancel_reject(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👑 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "export_data")
async def export_data(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    partners = db.get_all_partners()
    withdrawals = db.get_pending_withdrawals()
    
    if partners:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['User ID', 'Username', 'Full Name', 'Promo Code', 'Referrals', 'Balance', 'Status', 'Registered At'])
        
        for partner in partners:
            writer.writerow([
                partner['user_id'],
                partner['username'] or '',
                partner['full_name'],
                partner['promo_code'] or '',
                partner['referrals'],
                partner['balance'],
                'Active' if partner['is_active'] else 'Inactive',
                partner['registered_at']
            ])
        
        csv_data = output.getvalue()
        csv_file = BufferedInputFile(csv_data.encode(), filename="partners.csv")
        
        await callback.message.answer_document(
            document=csv_file,
            caption="📊 Экспорт данных партнеров"
        )
    
    if withdrawals:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'User ID', 'Username', 'Full Name', 'Amount', 'Requisites', 'Comment', 'Created At'])
        
        for withdrawal in withdrawals:
            writer.writerow([
                withdrawal['id'],
                withdrawal['user_id'],
                withdrawal['username'] or '',
                withdrawal['full_name'],
                withdrawal['amount'],
                withdrawal['requisites'],
                withdrawal['comment'] or '',
                withdrawal['created_at']
            ])
        
        csv_data = output.getvalue()
        csv_file = BufferedInputFile(csv_data.encode(), filename="withdrawals.csv")
        
        await callback.message.answer_document(
            document=csv_file,
            caption="📊 Экспорт заявок на вывод"
        )
    
    if not partners and not withdrawals:
        await callback.message.edit_text(
            "❌ Нет данных для экспорта",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "✅ Экспорт данных завершен!",
            reply_markup=get_admin_keyboard()
        )
    
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "👑 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()