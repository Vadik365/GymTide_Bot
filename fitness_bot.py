import os
import csv
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from typing import List
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_ID", "").split(",")))

print("ADMIN_IDS:", ADMIN_IDS)

# Logging
logging.basicConfig(level=logging.INFO)

# Bot and Dispatcher

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(
    parse_mode=ParseMode.HTML))

dp = Dispatcher(storage=MemoryStorage())

# Translations
translations = {
    'ru': {
        'greeting': "Привет! Я помогу составить тебе программу тренировок.",
        'choose_language': "Пожалуйста, выбери язык:",
        'thanks': "Спасибо! Ваша анкета отправлена тренеру.",
        'questions': [
            "Как тебя зовут?",
            "Сколько тебе лет?",
            "Какой у тебя вес?",
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
            "What is your main fitness goal?",
            "How often do you plan to work out?"
        ]
    }
}

questions = ["name", "age", "weight", "goal", "frequency"] 

lang_map = {
    "🇬🇧 English": "en",
    "🇺🇦 Українська": "uk",
    "🇷🇺 Русский": "ru"
}

lang_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=t)] for t in lang_map],
    resize_keyboard=True
)


class Form(StatesGroup):
    filling = State()


@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    save_username(message.from_user)
    if user_id in ADMIN_IDS:
        await message.answer("Привет, Админ!", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()
    await message.answer(translations['ru']['choose_language'], reply_markup=lang_keyboard)


@dp.message()
async def handle_message(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_state = await state.get_state()
    lang = user_data.get("lang")

    if message.text in lang_map:
        lang_code = lang_map[message.text]
        await state.update_data(lang=lang_code, current_question=0, answers={})
        await message.answer(translations[lang_code]['greeting'])
        await message.answer(translations[lang_code]['questions'][0])
        await state.set_state(Form.filling)
        return

    if current_state == Form.filling:
        await handle_answer(message, state)


async def handle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    index = data['current_question']
    answers = data.get("answers", {})

    answers[questions[index]] = message.text
    answers['username'] = message.from_user.username or "—"
    answers['language'] = lang

    index += 1
    if index < len(questions):
        await state.update_data(current_question=index, answers=answers)
        await message.answer(translations[lang]['questions'][index])
    else:
        await message.answer(translations[lang]['thanks'])
        await send_to_admin(message.from_user.id, answers)
        save_to_csv(message.from_user.id, answers)
        await state.clear()


async def send_to_admin(user_id: int, data: dict):
    text = (
        f"<b>Новая анкета</b>\n"
        f"Telegram ID: <code>{user_id}</code>\n"
        f"Username: @{data.get('username')}\n"
        f"Язык: {data.get('language')}\n"
        f"Имя: {data.get('name')}\n"
        f"Возраст: {data.get('age')}\n"
        f"Вес: {data.get('weight')}\n"
        f"Цель: {data.get('goal')}\n"
        f"Частота: {data.get('frequency')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logging.error(f"Failed to send to admin {admin_id}: {e}")


def save_to_csv(user_id: int, data: dict):
    file = "applications.csv"
    file_exists = os.path.exists(file)
    with open(file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["user_id", "username", "language"] + questions)

        writer.writerow([user_id, data.get("username", ""), data.get(
            "language", "")] + [data.get(q, "") for q in questions])


def save_username(user: types.User):
    if not user.username:
        return
    file = "users.csv"
    if not os.path.exists(file):
        with open(file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["username"])
    with open(file, "r") as f:
        usernames = [row[0] for row in csv.reader(f)]
    if user.username not in usernames:
        with open(file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([user.username])


@dp.message(Command("list"))
async def list_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if os.path.exists("applications.csv"):
        with open("applications.csv", encoding="utf-8") as f:
            lines = f.readlines()
            count = len(lines) - 1
            await message.answer(f"Всего анкет: {count}")
    else:
        await message.answer("Файл с анкетами не найден.")


@dp.message(Command("send"))
async def send_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # Только для админа

    args = message.text.split(maxsplit=2)

    if len(args) == 1:
        try:
            with open("applications.csv", "r", encoding="utf-8") as csvfile:
                rows = list(csv.reader(csvfile))
                text = ""
                for row in rows[1:]:  # пропускаем заголовок
                    text += (
                        f"\n\nTelegram ID: <code>{row[0]}</code>"
                        f"\nUsername: @{row[1]}"
                        f"\nЯзык: {row[2]}"
                        f"\nИмя: {row[3]}"
                        f"\nВозраст: {row[4]}"
                        f"\nВес: {row[5]}"
                        f"\nЦель: {row[6]}"
                        f"\nЧастота: {row[7]}"
                        f"\n{'-'*20}"
                    )
                if text:
                    await message.answer(f"<b>Список анкет:</b>{text}", parse_mode=ParseMode.HTML)
                else:
                    await message.answer("Анкет пока нет.")
        except FileNotFoundError:
            await message.answer("Файл с анкетами не найден.")
        return

    if len(args) >= 3:
        try:
            user_id = int(args[1])
            text_to_send = args[2]
            await bot.send_message(chat_id=user_id, text=text_to_send)
            await message.answer(f"✅ Сообщение отправлено пользователю {user_id}.")
        except ValueError:
            await message.answer("❌ user_id должен быть числом.")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка при отправке: {e}")
        return

    await message.answer("❗ Неверный формат. Используй:\n<b>/send user_id сообщение</b>", parse_mode=ParseMode.HTML)


@dp.message(Command("sendfile"))
async def send_file_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer("❗ Формат: /sendfile <user_id> <путь_к_файлу>")
    try:
        path = args[2]
        if not os.path.exists(path):
            return await message.answer("Файл не найден.")
        await bot.send_document(chat_id=int(args[1]), document=FSInputFile(path))
        await message.answer("📎 Файл отправлен.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
