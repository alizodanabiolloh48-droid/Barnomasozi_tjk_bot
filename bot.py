import os
import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ==================================================
# НАСТРОЙКА
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN ёфт нашуд!")

CHANNEL_ID = "@Barnomasozi_tjk"
CHANNEL_LINK = "https://t.me/barnomasozitjkkanal"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================================================
# DATABASE
# ==================================================

def init_db():
    conn = sqlite3.connect("bot_files.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ==================================================
# САНҶИШИ ОБУНА
# ==================================================

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        return member.status in (
            "creator",
            "administrator",
            "member"
        )

    except Exception as e:
        logging.error(f"Subscription error: {e}")
        return False


# ==================================================
# ТУГМАҲО
# ==================================================

def subscribe_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Обуна шудан",
                    url=CHANNEL_LINK
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Обуна шудам",
                    callback_data="check_sub"
                )
            ]
        ]
    )


# ==================================================
# САБТИ ФАЙЛҲО АЗ КАНАЛ
# ==================================================

@dp.channel_post()
async def save_channel_file(message: types.Message):

    file_id = None
    file_type = None
    file_name = None

    # APK / ZIP / PDF / дигар файлҳо
    if message.document:

        file_id = message.document.file_id
        file_type = "document"

        if message.caption:
            file_name = message.caption.strip()
        else:
            file_name = message.document.file_name

    # Видео
    elif message.video:

        file_id = message.video.file_id
        file_type = "video"

        if message.caption:
            file_name = message.caption.strip()
        else:
            file_name = "video"

    if not file_id or not file_name:
        return

    name = file_name.lower().strip()

    conn = sqlite3.connect("bot_files.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO files
        (name, file_id, file_type)
        VALUES (?, ?, ?)
        """,
        (
            name,
            file_id,
            file_type
        )
    )

    conn.commit()
    conn.close()

    logging.info(
        f"✅ Файл сабт шуд: {file_name}"
    )


# ==================================================
# /START
# ==================================================

@dp.message(CommandStart())
async def start_handler(message: types.Message):

    subscribed = await check_subscription(
        message.from_user.id
    )

    if not subscribed:

        await message.answer(
            "🔒 Барои истифодаи бот аввал ба канали мо обуна шавед.\n\n"
            "Баъд тугмаи «Обуна шудам»-ро пахш кунед.",
            reply_markup=subscribe_keyboard()
        )

        return

    await message.answer(
        "👋 Салом!\n\n"
        "🔎 Номи APK ё файлро нависед.\n"
        "Ман онро аз база меёбам."
    )


# ==================================================
# ТУГМАИ ОБУНА ШУДАМ
# ==================================================

@dp.callback_query(F.data == "check_sub")
async def check_subscription_button(
    callback: types.CallbackQuery
):

    subscribed = await check_subscription(
        callback.from_user.id
    )

    if subscribed:

        await callback.message.edit_text(
            "✅ Обуна тасдиқ шуд!\n\n"
            "🔎 Акнун номи APK ё файлро нависед."
        )

        await callback.answer("✅ Обуна тасдиқ шуд!")

    else:

        await callback.answer(
            "❌ Шумо ҳанӯз ба канал обуна нашудаед!",
            show_alert=True
        )


# ==================================================
# ҶУСТУҶӮИ ФАЙЛ
# ==================================================

@dp.message(F.text)
async def search_file(message: types.Message):

    # Аввал subscription
    subscribed = await check_subscription(
        message.from_user.id
    )

    if not subscribed:

        await message.answer(
            "🔒 Бе обуна ба канал бот кор намекунад.",
            reply_markup=subscribe_keyboard()
        )

        return

    query = message.text.lower().strip()

    if not query:
        await message.answer(
            "🔎 Номи файлро нависед."
        )
        return

    conn = sqlite3.connect("bot_files.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT file_id, file_type, name
        FROM files
        WHERE name LIKE ?
        ORDER BY id DESC
        """,
        (f"%{query}%",)
    )

    results = cursor.fetchall()

    conn.close()

    # Файл ёфт нашуд
    if not results:

        await message.answer(
            "❌ Файл ёфт нашуд.\n\n"
            f"🔎 Ҷустуҷӯ: {query}"
        )

        return

    # Натиҷаҳо
    await message.answer(
        f"✅ {len(results)} файл ёфт шуд:"
    )

    for file_id, file_type, name in results:

        try:

            if file_type == "document":

                await message.answer_document(
                    document=file_id,
                    caption=f"📦 {name}"
                )

            elif file_type == "video":

                await message.answer_video(
                    video=file_id,
                    caption=f"🎬 {name}"
                )

        except Exception as e:

            logging.error(
                f"Send file error: {e}"
            )


# ==================================================
# RUN
# ==================================================

async def main():

    logging.basicConfig(
        level=logging.INFO
    )

    print("🤖 Бот фаъол шуд...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
