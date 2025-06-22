import os
import csv
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, InputFile, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from typing import List

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_ID", "").split(",")))

# Настройка логгирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(
    parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения пользователей
USER_FILE = "users.csv"

# Кнопки выбора языка
language_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🇬🇧 English"),
            KeyboardButton(text="🇺🇦 Українська"),
            KeyboardButton(text="🇷🇺 Русский"),
        ]
    ],
    resize_keyboard=True
)

# Функция сохранения username


def save_username(user: types.User):
    if not user.username:
        return
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["username"])
    with open(USER_FILE, "r") as f:
        usernames = [row[0] for row in csv.reader(f)]
    if user.username not in usernames:
        with open(USER_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([user.username])

# Обработка команды /start


@dp.message(CommandStart())
async def cmd_start(message: Message):
    save_username(message.from_user)
    await message.answer("🌐 Please select your language:", reply_markup=language_kb)

# Обработка команды /send (только для админа)


@dp.message(Command("send"))
async def send_message_to_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔️ Access denied.")
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        return await message.answer("⚠️ Please provide message text: /send Your message here.")

    msg_text = text[1]
    sent = 0
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            for row in csv.reader(f):
                username = row[0]
                if username == "username":
                    continue
                try:
                    await bot.send_message(chat_id=f"@{username}", text=msg_text)
                    sent += 1
                except Exception as e:
                    logging.warning(f"Failed to send to @{username}: {e}")
    await message.answer(f"✅ Message sent to {sent} users.")

# Обработка команды /sendfile (только для админа)


@dp.message(Command("sendfile"))
async def send_file_to_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔️ Access denied.")
    file_path = "file_to_send.txt"
    if not os.path.exists(file_path):
        return await message.answer("⚠️ File not found.")

    sent = 0
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            for row in csv.reader(f):
                username = row[0]
                if username == "username":
                    continue
                try:
                    await bot.send_document(chat_id=f"@{username}", document=InputFile(file_path))
                    sent += 1
                except Exception as e:
                    logging.warning(f"Failed to send file to @{username}: {e}")
    await message.answer(f"✅ File sent to {sent} users.")

# Запуск бота
if __name__ == "__main__":
    import asyncio

    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())
