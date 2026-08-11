# Barnomasozi_tjk_botimport asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== СОЗНОМАҲО (НАСТРОЙКИ) ====================
BOT_TOKEN = "8842730589:AAFZDmYUR0hzkyrGBDvxYU7tXtcvIUoU_BI"
CHANNEL_ID = "@Barnomasozi_tjk"  # Масалан: @my_apps_channel ё ID: -100123456789
CHANNEL_LINK = "https://t.me/barnomasozitjkkanal"  # Силсилапайванди канал
# ==============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- 1. Сохтани базаи маълумот (SQLite) ---
def init_db():
    conn = sqlite3.connect('bot_files.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            file_id TEXT,
            file_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 2. Функсияи тафтиши обуна ба канал ---
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception as e:
        logging.error(f"Хатогӣ дар тафтиши обуна: {e}")
        return False

# Тугмаҳо барои обуна
def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Обуна шудан ба канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Обуна шудам (Тафтиш)", callback_data="check_sub")]
    ])

# --- 3. АВТОМАТИКӢ САБТ КАРДАНИ ФАЙЛ АЗ КАНАЛ ---
@dp.channel_post()
async def auto_save_from_channel(message: types.Message):
    file_id = None
    file_type = None
    file_name = ""

    # Агар APK ё дигар файл бошад
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        # Аввал аз текст (caption) номро мегирад, агар набуд аз номи худи APK
        file_name = message.caption or message.document.file_name or ""

    # Агар видео бошад
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.caption or message.video.file_name or "видео"

    # Агар файл пайдо шуд, ба база сабт мекунем
    if file_id and file_name:
        clean_name = file_name.lower().strip()
        conn = sqlite3.connect('bot_files.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO files (name, file_id, file_type) VALUES (?, ?, ?)',
            (clean_name, file_id, file_type)
        )
        conn.commit()
        conn.close()
        print(f"✅ Файли нав ба база сабт шуд: {file_name}")

# --- 4. КОРКАРДИ ФАРМОНИ /start ---
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    is_sub = await check_subscription(message.from_user.id)
    if is_sub:
        await message.answer("👋 Ассалому алейкум! Номи APK ё видеоро нависед, то онро пайдо кунам.")
    else:
        await message.answer(
            "⚠️ Барои истифодабарии бот, аввал бояд ба канали мо обуна шавед!",
            reply_markup=subscribe_keyboard()
        )

# --- 5. ТАФТИШИ ТУГМАИ "ОБУНА ШУДАМ" ---
@dp.callback_query(F.data == "check_sub")
async def check_button(callback: types.CallbackQuery):
    is_sub = await check_subscription(callback.from_user.id)
    if is_sub:
        await callback.message.delete()
        await callback.message.answer("✅ Раҳмат барои обуна! Акнун номи файлро нависед.")
    else:
        await callback.answer("❌ Шумо ҳануз ба канал обуна нашудаед!", show_alert=True)

# --- 6. ҶУСТУҶӮИ ФАЙЛ БО НОМ ---
@dp.message()
async def search_handler(message: types.Message):
    # Аввал тафтиш мекунем, ки корбар обуна аст ё не
    is_sub = await check_subscription(message.from_user.id)
    if not is_sub:
        await message.answer(
            "⚠️ Шумо ба канал обуна нашудаед! Аввал обуна шавед:",
            reply_markup=subscribe_keyboard()
        )
        return

    user_query = message.text.lower().strip()

    conn = sqlite3.connect('bot_files.db')
    cursor = conn.cursor()
    # Ҷустуҷӯ дар база (ҳатто агар як қисми номро нависад ҳам меёбад)
    cursor.execute('SELECT file_id, file_type, name FROM files WHERE name LIKE ?', (f'%{user_query}%',))
    results = cursor.fetchall()
    conn.close()

    if results:
        for file_id, file_type, name in results:
            if file_type == "document":
                await message.answer_document(document=file_id, caption=f"📦 {name}")
            elif file_type == "video":
                await message.answer_video(video=file_id, caption=f"🎬 {name}")
    else:
        await message.answer("🔍 Мутаассифона, бо ин ном ҳеҷ чиз ёфт нашуд. Номро аниқтар нависед.")

# --- РАВАНДИ ИҶРОИШ ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
