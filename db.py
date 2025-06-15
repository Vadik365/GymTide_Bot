# db.py

import aiosqlite
from datetime import datetime, timedelta

DB_NAME = "users.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
                         CREATE TABLE IF NOT EXISTS users
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             telegram_id
                             INTEGER
                             UNIQUE,
                             name
                             TEXT,
                             age
                             INTEGER,
                             weight
                             REAL,
                             health_issues
                             TEXT,
                             goal
                             TEXT,
                             gym_visits
                             INTEGER,
                             subscription_until
                             DATE,
                             referred_by
                             INTEGER,
                             referrals_count
                             INTEGER
                             DEFAULT
                             0
                         )
                         ''')
        await db.commit()


async def register_user(telegram_id: int, ref_id: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        existing_user = await cursor.fetchone()

        if existing_user:
            return False  # уже зарегистрирован

        referred_by = int(ref_id) if ref_id and ref_id.isdigit() else None
        sub_until = datetime.now() + timedelta(days=30)

        await db.execute('''
                         INSERT INTO users (telegram_id, subscription_until, referred_by)
                         VALUES (?, ?, ?)
                         ''', (telegram_id, sub_until.date(), referred_by))

        await db.commit()

        if referred_by:
            await db.execute('''
                             UPDATE users
                             SET referrals_count = referrals_count + 1
                             WHERE telegram_id = ?
                             ''', (referred_by,))
            await db.commit()

            cursor = await db.execute('SELECT referrals_count FROM users WHERE telegram_id = ?', (referred_by,))
            row = await cursor.fetchone()
            if row and row[0] == 3:
                await db.execute('''
                                 UPDATE users
                                 SET subscription_until = date (subscription_until, '+30 day')
                                 WHERE telegram_id = ?
                                 ''', (referred_by,))
                await db.commit()

        return True


# Обновление анкеты пользователя
async def update_user_data(telegram_id: int, field: str, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f'''
            UPDATE users
            SET {field} = ?
            WHERE telegram_id = ?
        ''', (value, telegram_id))
        await db.commit()
