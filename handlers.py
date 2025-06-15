# handlers.py

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import db

router = Router()


# FSM для анкеты
class Questionnaire(StatesGroup):
    name = State()
    age = State()
    weight = State()
    health_issues = State()
    goal = State()
    gym_visits = State()


# Старт по реферальной ссылке
@router.message(CommandStart(deep_link=True))
async def cmd_start_ref(message: Message, command: CommandStart, state: FSMContext):
    ref_id = command.args
    user_id = message.from_user.id
    new_user = await db.register_user(user_id, ref_id)

    if new_user:
        await message.answer("Добро пожаловать в GymTide! 🏋️\nТы зарегистрирован по реферальной ссылке.")
    else:
        await message.answer("Ты уже зарегистрирован в GymTide ✅")

    link = f"https://t.me/{(await message.bot.me()).username}?start={user_id}"
    await message.answer(f"Пригласи друзей по ссылке:\n{link}\n\nПригласи 3 друзей — получи месяц бесплатно!")

    # Запуск анкеты
    await message.answer("Давай заполним анкету. Введи своё имя:")
    await state.set_state(Questionnaire.name)


# Старт без реферала
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_user = await db.register_user(user_id)

    if new_user:
        await message.answer("Добро пожаловать в GymTide! 🏋️ Ты зарегистрирован.")
    else:
        await message.answer("Ты уже зарегистрирован в GymTide ✅")

    link = f"https://t.me/{(await message.bot.me()).username}?start={user_id}"
    await message.answer(f"Пригласи друзей по ссылке:\n{link}\n\nПригласи 3 друзей — получи месяц бесплатно!")

    # Запуск анкеты
    await message.answer("Давай заполним анкету. Введи своё имя:")
    await state.set_state(Questionnaire.name)


# Анкета — шаги

@router.message(Questionnaire.name)
async def process_name(message: Message, state: FSMContext):
    await db.update_user_data(message.from_user.id, "name", message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(Questionnaire.age)


@router.message(Questionnaire.age)
async def process_age(message: Message, state: FSMContext):
    await db.update_user_data(message.from_user.id, "age", message.text)
    await message.answer("Какой у тебя вес (в кг)?")
    await state.set_state(Questionnaire.weight)


@router.message(Questionnaire.weight)
async def process_weight(message: Message, state: FSMContext):
    await db.update_user_data(message.from_user.id, "weight", message.text)
    await message.answer("Есть ли у тебя противопоказания по здоровью?")
    await state.set_state(Questionnaire.health_issues)


@router.message(Questionnaire.health_issues)
async def process_health_issues(message: Message, state: FSMContext):
    await db.update_user_data(message.from_user.id, "health_issues", message.text)
    await message.answer("Какая у тебя цель? (Похудеть / Набрать массу / Поддержать форму / Другое)")
    await state.set_state(Questionnaire.goal)


@router.message(Questionnaire.goal)
async def process_goal(message: Message, state: FSMContext):
    await db.update_user_data(message.from_user.id, "goal", message.text)
    await message.answer("Сколько раз в неделю ты планируешь посещать спортзал?")
    await state.set_state(Questionnaire.gym_visits)


@router.message(Questionnaire.gym_visits)
async def process_gym_visits(message: Message, state: FSMContext):
    await db.update_user_data(message.from_user.id, "gym_visits", message.text)
    await message.answer("Спасибо! Анкета заполнена ✅\nСкоро ты получишь индивидуальную программу тренировок 💪")
    await state.clear()
