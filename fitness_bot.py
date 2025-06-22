import os
import csv
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, InputFile
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import Bot

# Загружаем переменные окружения
load_dotenv()

# Настройки
# Переменная из .env
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # ID администратора

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Мультиязычные сообщения
translations = {
    'ru': {
        'greeting': "Привет! Я помогу составить тебе программу тренировок.",
        'choose_language': "Пожалуйста, выбери язык:",
        'thanks': "Спасибо! Ваша анкета отправлена тренеру.",
        'questions': [
            "Как тебя зовут?",
            "Сколько тебе лет?",
            "Какой у тебя вес?",
            "Есть ли у тебя проблемы со здоровьем?",
            "Какая твоя основная фитнес-цель?",
            "Как часто ты планируешь заниматься?"
        ]
    },
    'uk': {
        'greeting': "Привіт! Я допоможу скласти для тебе програму тренувань.",
        'choose_language': "Будь ласка, обери мову:",
        'thanks': "Дякую! Твою анкету надіслано тренеру.",
        'questions': [
            "Як тебе звати?",
            "Скільки тобі років?",
            "Яка в тебе вага?",
            "Чи маєш проблеми зі здоров’ям?",
            "Яка твоя основна фітнес-мета?",
            "Як часто плануєш тренуватися?"
        ]
    },
    'en': {
        'greeting': "Hi! I’ll help you create a workout plan.",
        'choose_language': "Please choose a language:",
        'thanks': "Thanks! Your form has been sent to the coach.",
        'questions': [
            "What is your name?",
            "How old are you?",
            "What is your weight?",
            "Do you have any health problems?",
            "What is your main fitness goal?",
            "How often do you plan to work out?"
        ]
    }
}

# Порядок вопросов и ключи для CSV
questions = [
    ("name", "name"),
    ("age", "age"),
    ("weight", "weight"),
    ("health", "health"),
    ("goal", "goal"),
    ("frequency", "frequency")
]

# Клавиатура выбора языка
lang_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇬🇧 English"), KeyboardButton(
            text="🇺🇦 Українська"), KeyboardButton(text="🇷🇺 Русский")]
    ],
    resize_keyboard=True
)

lang_map = {
    "🇬🇧 English": "en",
    "🇺🇦 Українська": "uk",
    "🇷🇺 Русский": "ru",
}

# Состояния FSM


class Form(StatesGroup):
    filling = State()

# Команда /start


@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        admin_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="/list")],
                      [KeyboardButton(text="/sendfile")]],
            resize_keyboard=True
        )
        await message.answer(f"Привет, Админ!\nТвой Telegram ID: {user_id}", reply_markup=admin_keyboard)
        await state.clear()
    else:
        await message.answer(translations['ru']['choose_language'], reply_markup=lang_keyboard)
        await state.clear()

# Выбор языка и начало анкеты


@dp.message()
async def process_language_or_answer(message: Message, state: FSMContext):
    lang = lang_map.get(message.text)
    current_state = await state.get_state()

    if lang:
        await state.update_data(lang=lang, current_question=0, answers={})
        await message.answer(translations[lang]['greeting'])
        await message.answer(translations[lang]['questions'][0])
        await state.set_state(Form.filling)
        return

    if current_state == Form.filling:
        await process_question(message, state)

# Обработка ответов на анкету


async def process_question(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    index = data.get("current_question", 0)
    answers = data.get("answers", {})

    key = questions[index][0]
    answers[key] = message.text

    # Сохраняем язык и username
    answers["language"] = lang
    answers["username"] = message.from_user.username or "—"

    index += 1
    if index < len(questions):
        await state.update_data(current_question=index, answers=answers)
        await message.answer(translations[lang]['questions'][index])
    else:
        await message.answer(translations[lang]['thanks'])
        await send_to_admin(message.from_user.id, answers)
        save_to_csv(message.from_user.id, answers)
        await state.clear()

# Отправка анкеты админу


async def send_to_admin(user_id: int, data: dict):
    text = (
        "<b>Новая анкета</b>\n\n"
        f"Telegram ID: <code>{user_id}</code>\n"
        f"Username: @{data.get('username')}\n"
        f"Язык: {data.get('language')}\n"
        f"Имя: {data.get('name')}\n"
        f"Возраст: {data.get('age')}\n"
        f"Вес: {data.get('weight')}\n"
        f"Здоровье: {data.get('health')}\n"
        f"Цель: {data.get('goal')}\n"
        f"Частота: {data.get('frequency')}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=ParseMode.HTML)

# Сохранение анкеты


def save_to_csv(user_id: int, data: dict):
    file_exists = os.path.isfile("applications.csv")
    with open("applications.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["user_id", "username", "language"] + [q[0]
                            for q in questions])
        writer.writerow([user_id, data.get("username", ""), data.get(
            "language", "")] + [data.get(q[0], "") for q in questions])

# Команда /list


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open("applications.csv", encoding="utf-8") as f:
            rows = f.readlines()
            await message.answer(f"Всего анкет: {len(rows)-1 if len(rows) > 1 else 0}")
    except FileNotFoundError:
        await message.answer("Файл с анкетами не найден.")

# Команда /send <user_id> <сообщение>


@dp.message(Command("send"))
async def cmd_send(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❗ Формат: /send <user_id> <сообщение>")
        return
    try:
        user_id = int(args[1])
        text = args[2]
        await bot.send_message(chat_id=user_id, text=text)
        await message.answer(f"✅ Сообщение отправлено пользователю {user_id}.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")

# Команда /sendfile <user_id> <путь_к_файлу>


@dp.message(Command("sendfile"))
async def cmd_sendfile(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❗ Формат: /sendfile <user_id> <путь_к_файлу>")
        return
    try:
        user_id = int(args[1])
        path = args[2]
        if not os.path.exists(path):
            await message.answer("❌ Файл не найден.")
            return
        await bot.send_document(chat_id=user_id, document=InputFile(path))
        await message.answer("📎 Файл отправлен.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при отправке: {e}")

# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)
