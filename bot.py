import os
import logging
import sqlite3

from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)


# ==================================================
# SETTINGS
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN ёфт нашуд!")

if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL ёфт нашуд!")


CHANNEL_ID = "@barnomasozitjkkanal"
CHANNEL_LINK = "https://t.me/barnomasozitjkkanal"

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"


# ==================================================
# BOT
# ==================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================================================
# DATABASE
# ==================================================

DB_NAME = "bot_files.db"


def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    logging.info("✅ Database тайёр аст")


init_db()


# ==================================================
# SUBSCRIPTION
# ==================================================

async def check_subscription(user_id: int):

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

        logging.error(
            "Subscription error: %s",
            e
        )

        return False


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
# SAVE CHANNEL FILE
# ==================================================

@dp.channel_post()
async def save_channel_file(
    message: types.Message
):

    file_id = None
    file_type = None
    file_name = None

    # DOCUMENT
    if message.document:

        file_id = message.document.file_id
        file_type = "document"
        file_name = (
            message.document.file_name
            or "document"
        )

    # VIDEO
    elif message.video:

        file_id = message.video.file_id
        file_type = "video"
        file_name = "video"

    # PHOTO
    elif message.photo:

        file_id = message.photo[-1].file_id
        file_type = "photo"
        file_name = "photo"

    # AUDIO
    elif message.audio:

        file_id = message.audio.file_id
        file_type = "audio"
        file_name = (
            message.audio.file_name
            or "audio"
        )

    if not file_id:
        return

    name = file_name.lower()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO files
        (
            name,
            file_id,
            file_type,
            message_id,
            channel_id
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            file_id,
            file_type,
            message.message_id,
            str(message.chat.id)
        )
    )

    conn.commit()
    conn.close()

    logging.info(
        "✅ Файл сабт шуд: %s",
        file_name
    )


# ==================================================
# START
# ==================================================

@dp.message(CommandStart())
async def start(message: types.Message):

    if not message.from_user:
        return

    subscribed = await check_subscription(
        message.from_user.id
    )

    if not subscribed:

        await message.answer(
            "🔒 Аввал ба канал обуна шавед.",
            reply_markup=subscribe_keyboard()
        )

        return

    await message.answer(
        "👋 Салом!\n\n"
        "🔎 Номи файлро нависед."
    )


# ==================================================
# CHECK SUBSCRIPTION BUTTON
# ==================================================

@dp.callback_query(F.data == "check_sub")
async def check_button(callback):

    subscribed = await check_subscription(
        callback.from_user.id
    )

    if subscribed:

        await callback.message.edit_text(
            "✅ Обуна тасдиқ шуд.\n\n"
            "🔎 Номи файлро нависед."
        )

        await callback.answer()

    else:

        await callback.answer(
            "❌ Ҳоло обуна нестед!",
            show_alert=True
        )


# ==================================================
# SEARCH
# ==================================================

@dp.message(F.text)
async def search(message: types.Message):

    if not message.from_user:
        return

    subscribed = await check_subscription(
        message.from_user.id
    )

    if not subscribed:

        await message.answer(
            "🔒 Ба канал обуна шавед.",
            reply_markup=subscribe_keyboard()
        )

        return

    query = message.text.strip().lower()

    if not query:
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            file_id,
            file_type,
            name,
            message_id,
            channel_id
        FROM files
        WHERE name LIKE ?
        ORDER BY id DESC
        """,
        (
            f"%{query}%",
        )
    )

    results = cursor.fetchall()

    conn.close()

    if not results:

        await message.answer(
            "❌ Файл ёфт нашуд."
        )

        return

    found = False

    for (
        file_id,
        file_type,
        name,
        message_id,
        channel_id
    ) in results:

        try:

            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=channel_id,
                message_id=message_id
            )

            found = True

        except Exception as e:

            logging.warning(
                "Файл дигар дастрас нест: %s",
                e
            )

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM files
                WHERE message_id=?
                AND channel_id=?
                """,
                (
                    message_id,
                    channel_id
                )
            )

            conn.commit()
            conn.close()

    if not found:

        await message.answer(
            "❌ Файл ёфт нашуд ё дигар дар канал мавҷуд нест."
        )


# ==================================================
# HEALTH CHECK
# ==================================================

async def health(request):

    return web.Response(
        text="🤖 Barnomasozi TJK Bot is running!"
    )


# ==================================================
# TELEGRAM WEBHOOK
# ==================================================

async def telegram_webhook(request):

    try:

        data = await request.json()

        update = Update.model_validate(
            data,
            context={
                "bot": bot
            }
        )

        await dp.feed_update(
            bot,
            update
        )

        return web.Response(
            text="OK"
        )

    except Exception as e:

        logging.exception(
            "❌ Webhook error"
        )

        return web.Response(
            status=500,
            text=str(e)
        )


# ==================================================
# STARTUP
# ==================================================

async def on_startup(app):

    webhook_url = (
        WEBHOOK_URL
        + WEBHOOK_PATH
    )

    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True
    )

    logging.info(
        "✅ Webhook установлен: %s",
        webhook_url
    )


# ==================================================
# SHUTDOWN
# ==================================================

async def on_shutdown(app):

    try:

        await bot.delete_webhook()

        logging.info(
            "✅ Webhook удалён"
        )

    except Exception as e:

        logging.error(
            "Webhook delete error: %s",
            e
        )

    await bot.session.close()


# ==================================================
# WEB SERVER
# ==================================================

app = web.Application()

app.router.add_get(
    "/",
    health
)

app.router.add_post(
    WEBHOOK_PATH,
    telegram_webhook
)

app.on_startup.append(
    on_startup
)

app.on_cleanup.append(
    on_shutdown
)


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO
    )

    logging.info(
        "🚀 Barnomasozi TJK Bot starting..."
    )

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
