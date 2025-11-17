from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TEST_QUESTIONS, MATERIALS_CHANNEL, ADMIN_IDS, STARTER_PACK_LINK, INFO_LINK, SUPPORT_LINK
from database import Database
from keyboards import *

router = Router()
db = Database()

class TestStates(StatesGroup):
    name = State()
    answering = State()

class WithdrawalStates(StatesGroup):
    amount = State()
    requisites = State()
    comment = State()

class PromoCodeStates(StatesGroup):
    waiting_for_promo = State()

def check_registration(user_id):
    partner = db.get_partner(user_id)
    return partner and partner['is_active']

async def notify_admins(bot, message_text):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message_text)
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

@router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    
    db.add_partner(user_id, username, full_name)
    
    is_admin = user_id in ADMIN_IDS
    is_registered = check_registration(user_id)
    
    if is_registered:
        await message.answer(
            "👋 С возвращением в партнерскую программу LEXINST!\n\n"
            "Выберите раздел в меню ниже:",
            reply_markup=get_main_keyboard(is_admin)
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в партнерскую программу LEXINST!\n\n"
            "Для доступа ко всем функциям необходимо пройти регистрацию.\n"
            "Нажмите '🤝 Сотрудничество' чтобы начать.",
            reply_markup=get_main_keyboard(is_admin)
        )

@router.message(F.text == "👤 Личный кабинет")
async def personal_cabinet(message: Message):
    if not check_registration(message.from_user.id):
        await message.answer("❌ Доступно только после регистрации. Пройдите тест и создайте промокод в разделе '🤝 Сотрудничество'")
        return
    
    await message.answer(
        "👤 Личный кабинет\n\n"
        "Выберите действие:",
        reply_markup=get_lk_keyboard()
    )

@router.message(F.text == "🤝 Сотрудничество")
async def cooperation(message: Message):
    partner = db.get_partner(message.from_user.id)
    if not partner:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return
    
    is_registered = partner['is_active']
    
    if is_registered:
        await message.answer(
            "🤝 Сотрудничество\n\n"
            "Выберите действие:",
            reply_markup=get_cooperation_registered_keyboard()
        )
    else:
        await message.answer(
            "🤝 Сотрудничество\n\n"
            "Для доступа к материалам необходимо пройти регистрацию:",
            reply_markup=get_cooperation_unregistered_keyboard()
        )

@router.message(F.text == "💬 Связь с поддержкой")
async def support(message: Message):
    if not check_registration(message.from_user.id):
        await message.answer("❌ Доступно только после регистрации. Пройдите тест и создайте промокод в разделе '🤝 Сотрудничество'")
        return
    
    await message.answer(
        f"💬 Связь с поддержкой\n\n"
        f"По всем вопросам обращайтесь: {SUPPORT_LINK}",
        reply_markup=get_back_inline_keyboard()
    )

@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    if not check_registration(callback.from_user.id):
        await callback.answer("❌ Доступно только после регистрации", show_alert=True)
        return
    
    partner = db.get_partner(callback.from_user.id)
    if partner:
        registered_date = partner['registered_at']
        if isinstance(registered_date, str):
            registered_date = registered_date.split(' ')[0]
        
        await callback.message.edit_text(
            f"📊 Ваша статистика:\n\n"
            f"👤 Имя: {partner['full_name']}\n"
            f"🎁 Промокод: {partner['promo_code'] or 'не создан'}\n"
            f"👥 Рефералов: {partner['referrals']}\n"
            f"💰 Баланс: {partner['balance']} руб.\n"
            f"📅 Регистрация: {registered_date}",
            reply_markup=get_lk_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "article")
async def show_article(callback: CallbackQuery):
    if not check_registration(callback.from_user.id):
        await callback.answer("❌ Доступно только после регистрации", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📖 Материалы для партнеров:\n\n"
        "Используйте эти ресурсы для эффективной работы:",
        reply_markup=get_article_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "materials")
async def show_materials(callback: CallbackQuery):
    if not check_registration(callback.from_user.id):
        await callback.answer("❌ Доступно только после регистрации", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📚 Канал с материалами для партнеров:",
        reply_markup=get_materials_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "start_test")
async def start_test(callback: CallbackQuery, state: FSMContext):
    partner = db.get_partner(callback.from_user.id)
    if partner and partner['is_active']:
        await callback.answer("Вы уже прошли регистрацию!", show_alert=True)
        return
    
    await state.set_state(TestStates.name)
    await state.update_data(answers=[], current_question=0)
    
    await callback.message.edit_text(
        TEST_QUESTIONS[0]['question'],
        reply_markup=None
    )
    await callback.answer()

@router.message(TestStates.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(user_name=message.text, current_question=1)
    await state.set_state(TestStates.answering)
    
    question_data = TEST_QUESTIONS[1]
    keyboard = get_test_keyboard(1, question_data)
    
    await message.answer(
        f"Вопрос 1/10:\n\n{question_data['question']}",
        reply_markup=keyboard
    )

@router.callback_query(TestStates.answering, F.data.startswith("answer_"))
async def process_test_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_question = data['current_question']
    answers = data['answers']
    
    answer_index = int(callback.data.split("_")[1])
    answers.append(answer_index)
    
    current_question += 1
    
    if current_question < len(TEST_QUESTIONS):
        await state.update_data(answers=answers, current_question=current_question)
        
        question_data = TEST_QUESTIONS[current_question]
        keyboard = get_test_keyboard(current_question, question_data)
        
        await callback.message.edit_text(
            f"Вопрос {current_question}/10:\n\n{question_data['question']}",
            reply_markup=keyboard
        )
    else:
        await finish_test(callback, state, answers)
    
    await callback.answer()

async def finish_test(callback: CallbackQuery, state: FSMContext, answers):
    correct_answers = 0
    total_questions = len(TEST_QUESTIONS) - 1
    
    for i in range(1, len(TEST_QUESTIONS)):
        if answers[i-1] == TEST_QUESTIONS[i]['correct']:
            correct_answers += 1
    
    score_percentage = (correct_answers / total_questions) * 100
    
    db.save_test_result(callback.from_user.id, correct_answers, total_questions)
    
    if score_percentage >= 80:
        await callback.message.edit_text(
            f"🎉 Поздравляем! Тест пройден успешно!\n\n"
            f"Ваш результат: {correct_answers}/{total_questions} ({score_percentage:.1f}%)\n\n"
            f"Теперь создайте свой промокод чтобы завершить регистрацию.",
            reply_markup=get_cooperation_after_test_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"❌ Тест не пройден\n\n"
            f"Ваш результат: {correct_answers}/{total_questions} ({score_percentage:.1f}%)\n"
            f"Необходимо набрать не менее 80% правильных ответов.\n\n"
            f"Попробуйте еще раз!",
            reply_markup=get_cooperation_unregistered_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "create_promo")
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    partner = db.get_partner(callback.from_user.id)
    if not partner:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    if partner['promo_code']:
        await callback.answer("У вас уже есть промокод!", show_alert=True)
        return
    
    await state.set_state(PromoCodeStates.waiting_for_promo)
    await callback.message.edit_text(
        "🎁 Создание промокода\n\n"
        "Придумайте ваш уникальный промокод (только латинские буквы и цифры):",
        reply_markup=get_back_inline_keyboard()
    )
    await callback.answer()

@router.message(PromoCodeStates.waiting_for_promo)
async def process_promo_code(message: Message, state: FSMContext):
    promo_code = message.text.strip()
    
    if not promo_code.isalnum():
        await message.answer("Промокод должен содержать только латинские буквы и цифры. Попробуйте еще раз:")
        return
    
    success = db.set_promo_code(message.from_user.id, promo_code)
    
    if success:
        await message.answer(
            f"🎉 Регистрация завершена!\n\n"
            f"Ваш промокод: <code>{promo_code}</code>\n\n"
            f"Теперь у вас есть доступ ко всем функциям бота.\n"
            f"Используйте меню для навигации.",
            reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
        )
    else:
        await message.answer(
            "❌ Этот промокод уже занят. Пожалуйста, придумайте другой:",
            reply_markup=get_back_inline_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "withdraw")
async def start_withdrawal(callback: CallbackQuery, state: FSMContext):
    if not check_registration(callback.from_user.id):
        await callback.answer("❌ Доступно только после регистрации", show_alert=True)
        return
    
    partner = db.get_partner(callback.from_user.id)
    if partner:
        balance = partner['balance']
        
        if balance < 1500:
            await callback.answer(
                f"Минимальная сумма для вывода - 1500 руб. Ваш баланс: {balance} руб.", 
                show_alert=True
            )
            return
        
        await state.set_state(WithdrawalStates.amount)
        await state.update_data(balance=balance)
        
        await callback.message.edit_text(
            f"💸 Запрос на вывод средств\n\n"
            f"Ваш баланс: {balance} руб.\n"
            f"Минимальная сумма вывода: 1500 руб.\n\n"
            f"Введите сумму для вывода:",
            reply_markup=get_back_inline_keyboard()
        )
    await callback.answer()

@router.message(WithdrawalStates.amount)
async def process_withdrawal_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        balance = data['balance']
        
        if amount < 1500:
            await message.answer("Минимальная сумма вывода - 1500 руб. Введите сумму еще раз:")
            return
        
        if amount > balance:
            await message.answer(f"Недостаточно средств. Ваш баланс: {balance} руб. Введите сумму еще раз:")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(WithdrawalStates.requisites)
        
        await message.answer(
            "Введите реквизиты для перевода (номер карты, счет и т.д.):",
            reply_markup=get_back_inline_keyboard()
        )
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму:")

@router.message(WithdrawalStates.requisites)
async def process_withdrawal_requisites(message: Message, state: FSMContext):
    await state.update_data(requisites=message.text)
    await state.set_state(WithdrawalStates.comment)
    
    await message.answer(
        "Введите комментарий к заявке (необязательно):",
        reply_markup=get_back_inline_keyboard()
    )

@router.message(WithdrawalStates.comment)
async def process_withdrawal_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    requisites = data['requisites']
    comment = message.text
    
    success = db.create_withdrawal_request(
        message.from_user.id, amount, requisites, comment
    )
    
    if success:
        partner = db.get_partner(message.from_user.id)
        
        withdrawals = db.get_pending_withdrawals()
        if withdrawals:
            our_withdrawal = None
            for w in withdrawals:
                if w['user_id'] == message.from_user.id and float(w['amount']) == float(amount):
                    our_withdrawal = w
                    break
            
            if our_withdrawal:
                withdrawal_id = our_withdrawal['id']
                
                withdrawal_notification = (
                    "🚨 НОВАЯ ЗАЯВКА НА ВЫВОД\n\n"
                    f"🆔 ID заявки: #{withdrawal_id}\n"
                    f"👤 Партнер: {partner['full_name']}\n"
                    f"📱 ID: {message.from_user.id}\n"
                    f"💰 Сумма: {amount} руб.\n"
                    f"💳 Реквизиты: {requisites}\n"
                )
                
                if comment:
                    withdrawal_notification += f"💬 Комментарий: {comment}\n"
                
                for admin_id in ADMIN_IDS:
                    try:
                        await message.bot.send_message(
                            admin_id, 
                            withdrawal_notification,
                            reply_markup=get_withdrawal_actions_keyboard(withdrawal_id)
                        )
                    except Exception as e:
                        print(f"Failed to notify admin {admin_id}: {e}")
        
        await message.answer(
            "✅ Ваша заявка на вывод успешно отправлена!\n\n"
            "Перевод придёт в течение суток(зависит от банка). "
            "Если возникли какие-то вопросы или трудности пишите в поддержку.",
            reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
        )
    else:
        await message.answer(
            "❌ Произошла ошибка при создании заявки. Попробуйте позже.",
            reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
        )
    
    await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    
    await callback.message.answer(
        "👋 Добро пожаловать в партнерскую программу LEXINST!\n\n"
        "Выберите раздел в меню ниже:",
        reply_markup=get_main_keyboard(is_admin)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_cooperation")
async def back_to_cooperation(callback: CallbackQuery):
    partner = db.get_partner(callback.from_user.id)
    is_registered = partner and partner['is_active']
    
    if is_registered:
        await callback.message.edit_text(
            "🤝 Сотрудничество\n\n"
            "Выберите действие:",
            reply_markup=get_cooperation_registered_keyboard()
        )
    else:
        await callback.message.edit_text(
            "🤝 Сотрудничество\n\n"
            "Для доступа к материалам необходимо пройти регистрацию:",
            reply_markup=get_cooperation_unregistered_keyboard()
        )
    await callback.answer()