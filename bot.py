import os
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from enkanetwork import EnkaNetworkAPI
from encbanner import ENC

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Please set BOT_TOKEN environment variable.")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DB_PATH = "users.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, uid TEXT)"
        )
        await db.commit()

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply(
        "Welcome! Send your Genshin UID with /register <UID> to link your account."
    )

@dp.message_handler(commands=["register"])
async def register_cmd(message: types.Message):
    args = message.get_args().strip()
    if not args.isdigit():
        return await message.reply("Please provide a valid UID (numbers only).")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (telegram_id, uid) VALUES (?, ?)",
            (message.from_user.id, args),
        )
        await db.commit()
    await message.reply(f"UID {args} registered successfully!")

@dp.message_handler(commands=["stats"])
async def stats_cmd(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT uid FROM users WHERE telegram_id = ?", (message.from_user.id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return await message.reply("You need to register first with /register <UID>.")

    uid = row[0]
    try:
        enc = ENC(uid=uid, lang="en")
        file_path = f"{uid}_stats.png"
        enc.save(file_path)
        with open(file_path, "rb") as photo:
            await message.reply_photo(photo)
        os.remove(file_path)
    except Exception as e:
        await message.reply(f"Error fetching stats: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)
