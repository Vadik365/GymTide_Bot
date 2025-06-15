import logging
import csv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Настройки
API_TOKEN = "7345572170:AAEH7Cf6IZC4t48hWUkOfqL8Qh7SB9kFVZ4"  # Вставь сюда свой токен!
ADMIN_ID = 7678402237  # Твой ID

# Логирование
logging.basicConfig(level=logging.INFO)

# Бот и диспетчер
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Переводы
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

questions = [
    ("name", "name"),
    ("age", "age"),
    ("weight", "weight"),
    ("health", "health"),
    ("goal", "goal"),
    ("frequency", "frequency")
]

# FSM состояния
class Form(StatesGroup):
    filling = State()

# Языковая клавиатура
lang_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇺🇦 Українська"), KeyboardButton(text="🇷🇺 Русский")]
    ],
    resize_keyboard=True
)

lang_map = {
    "🇬🇧 English": "en",
    "🇺🇦 Українська": "uk",
    "🇷🇺 Русский": "ru",
}

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        admin_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="/list")],
                [KeyboardButton(text="/send")]
            ],
            resize_keyboard=True
        )
        await message.answer(f"Твой Telegram ID: {user_id}\nПривет, Админ! Ты можешь использовать команды /list и /send.",
                             reply_markup=admin_keyboard)
        await state.clear()
    else:
        await message.answer("Please choose a language / Будь ласка, обери мову/ Пожалуйста, выбери язык :", reply_markup=lang_keyboard)
        await state.clear()

# Выбор языка
@dp.message()
async def choose_language(message: Message, state: FSMContext):
    lang = lang_map.get(message.text)
    if lang:
        await state.update_data(lang=lang, current_question=0, answers={})
        await message.answer(translations[lang]['greeting'])
        await message.answer(translations[lang]['questions'][0])
        await state.set_state(Form.filling)
        return

    # Если уже в процессе анкеты
    current_state = await state.get_state()
    if current_state == Form.filling:
        await process_answer(message, state)

# Обработка ответов на вопросы
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    current_index = data.get("current_question", 0)
    answers = data.get("answers", {})

    key = questions[current_index][0]
    answers[key] = message.text

    if "language" not in answers:
        answers["language"] = lang

    current_index += 1
    if current_index < len(questions):
        await state.update_data(current_question=current_index, answers=answers)
        await message.answer(translations[lang]['questions'][current_index])
    else:
        await message.answer(translations[lang]['thanks'])
        await send_application_to_admin(message.from_user.id, answers)
        save_to_csv(message.from_user.id, answers)
        await state.clear()

# Отправка анкеты админу
async def send_application_to_admin(user_id, data):
    language = data.get('language', 'не указан')
    text = (
        f"<b>Новая анкета</b>\n\n"
        f"Telegram ID: {user_id}\n"
        f"Язык: {data.get('language', 'не указан')}\n"
        f"Имя: {data.get('name', '')}\n"
        f"Возраст: {data.get('age', '')}\n"
        f"Вес: {data.get('weight', '')}\n"
        f"Здоровье: {data.get('health', '')}\n"
        f"Цель: {data.get('goal', '')}\n"
        f"Частота занятий: {data.get('frequency', '')}"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=ParseMode.HTML)

# Сохранение в CSV
def save_to_csv(user_id, data):
    with open("applications.csv", "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        row = [user_id, data.get("language", "")] + [data.get(q[0], "") for q in questions]
        writer.writerow(row)

# Команда /list
@dp.message(Command("list"))
async def cmd_list(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open("applications.csv", "r", encoding="utf-8") as csvfile:
            rows = csvfile.readlines()
            if not rows:
                await message.answer("Анкет пока нет.")
                return
            text = f"Всего анкет: {len(rows)}"
            await message.answer(text)
    except FileNotFoundError:
        await message.answer("Файл с анкетами не найден.")

# Команда /send
@dp.message(Command("send"))
async def handle_send_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=2)

    if len(args) == 1:
        try:
            with open("applications.csv", "r", encoding="utf-8") as csvfile:
                rows = csv.reader(csvfile)
                text = ""
                for row in rows:
                    text += (
                        f"\n\nTelegram ID: {row[0]}"
                        f"\nИмя: {row[1]}"
                        f"\nВозраст: {row[2]}"
                        f"\nВес: {row[3]}"
                        f"\nЗдоровье: {row[4]}"
                        f"\nЦель: {row[5]}"
                        f"\nЧастота занятий: {row[6]}"
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
            await message.answer(f"Сообщение отправлено пользователю {user_id}.")
        except ValueError:
            await message.answer("❌ user_id должен быть числом.")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка: {e}")
        return

    await message.answer("❗ Неверный формат. Используй /send <user_id> <сообщение>")

# Запуск
if __name__ == "__main__":
    dp.run_polling(bot)
