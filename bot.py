import os
import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN ёфт нашуд!")


CHANNEL_ID = "@barnomasozitjkkanal"
CHANNEL_LINK = "https://t.me/barnomasozitjkkanal"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ================= DATABASE =================

def init_db():

    conn = sqlite3.connect("bot_files.db")
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


init_db()


# ================= SUBSCRIBE =================

async def check_subscription(user_id):

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

        logging.error(e)
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



# ================= SAVE FILE =================

@dp.channel_post()
async def save_channel_file(message: types.Message):

    file_id = None
    file_type = None
    file_name = None


    if message.document:

        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name


    elif message.video:

        file_id = message.video.file_id
        file_type = "video"
        file_name = "video"



    if not file_id:
        return


    name = file_name.lower()


    conn = sqlite3.connect("bot_files.db")
    cursor = conn.cursor()


    cursor.execute(
        """
        INSERT INTO files
        (name,file_id,file_type,message_id,channel_id)
        VALUES(?,?,?,?,?)
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
        f"✅ Файл сабт шуд: {file_name}"
    )



# ================= START =================

@dp.message(CommandStart())
async def start(message: types.Message):

    if not await check_subscription(
        message.from_user.id
    ):

        await message.answer(
            "🔒 Аввал ба канал обуна шавед.",
            reply_markup=subscribe_keyboard()
        )

        return


    await message.answer(
        "👋 Салом!\n\n"
        "🔎 Номи файлро нависед."
    )



# ================= CHECK BUTTON =================

@dp.callback_query(F.data=="check_sub")
async def check_button(callback):

    if await check_subscription(
        callback.from_user.id
    ):

        await callback.message.edit_text(
            "✅ Обуна тасдиқ шуд.\n\n"
            "🔎 Номи файлро нависед."
        )

    else:

        await callback.answer(
            "❌ Ҳоло обуна нестед!",
            show_alert=True
        )



# ================= SEARCH =================

@dp.message(F.text)
async def search(message: types.Message):


    if not await check_subscription(
        message.from_user.id
    ):

        await message.answer(
            "🔒 Ба канал обуна шавед.",
            reply_markup=subscribe_keyboard()
        )

        return



    query = message.text.lower()



    conn = sqlite3.connect("bot_files.db")
    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT file_id,file_type,name,message_id,channel_id
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



    for file_id,file_type,name,message_id,channel_id in results:


        try:

            # санҷиши мавҷуд будани файл дар канал

            await bot.forward_message(
                chat_id=message.chat.id,
                from_chat_id=channel_id,
                message_id=message_id
            )


        except Exception:


            conn = sqlite3.connect(
                "bot_files.db"
            )

            cursor = conn.cursor()


            cursor.execute(
                "DELETE FROM files WHERE message_id=?",
                (message_id,)
            )


            conn.commit()
            conn.close()



            await message.answer(
                f"❌ {name} дигар дар канал нест."
            )



# ================= RUN =================

async def main():

    logging.basicConfig(
        level=logging.INFO
    )

    print("🤖 Бот фаъол шуд")

    await dp.start_polling(bot)



if __name__=="__main__":

    asyncio.run(main())
