import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = "8812359863:AAG6-Ww1pbCNuzHO4GkNAXTCE3fG7Dg4swY"

ADMIN_ID = 8279536115

REQUIRED_CHANNELS = [
    {
        "username": "@kino_tarjimaa_uzz",
        "link": "https://t.me/kino_tarjimaa_uzz"
    }
]


# =========================
# BOT
# =========================

bot = Bot(
    token=BOT_TOKEN,
    parse_mode="HTML"
)

from aiogram.contrib.fsm_storage.memory import MemoryStorage

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# =========================
# DATABASE
# =========================

conn = sqlite3.connect("kino.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_id TEXT NOT NULL
)
""")

conn.commit()


# =========================
# HOLAT
# =========================

class MovieState(StatesGroup):
    waiting_video = State()


# =========================
# OBUNA TEKSHIRISH
# =========================

async def check_subscription(user_id):

    for channel in REQUIRED_CHANNELS:

        try:

            member = await bot.get_chat_member(
                channel["username"],
                user_id
            )

            if member.status not in [
                "member",
                "administrator",
                "creator"
            ]:
                return False

        except Exception:

            return False

    return True


# =========================
# OBUNA TUGMALARI
# =========================

def subscription_keyboard():

    keyboard = []

    for channel in REQUIRED_CHANNELS:

        keyboard.append([
            InlineKeyboardButton(
                text="📢 Kanalga obuna bo‘lish",
                url=channel["link"]
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="✅ Obunani tekshirish",
            callback_data="check_subscription"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# =========================
# START
# =========================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    subscribed = await check_subscription(
        message.from_user.id
    )

    if not subscribed:

        await message.answer(
            "🎬 <b>Kino bot</b>\n\n"
            "Botdan foydalanish uchun kanalga "
            "obuna bo‘ling:",
            reply_markup=subscription_keyboard()
        )

        return

    await message.answer(
        "🎬 <b>Kino botga xush kelibsiz!</b>\n\n"
        "Kino kodini yuboring."
    )


# =========================
# OBUNANI QAYTA TEKSHIRISH
# =========================

@dp.callback_query_handler(
    lambda call: call.data == "check_subscription"
)
async def check_subscription_callback(
    callback: types.CallbackQuery
):

    subscribed = await check_subscription(
        callback.from_user.id
    )

    if subscribed:

        await callback.message.edit_text(
            "✅ <b>Obuna tasdiqlandi!</b>\n\n"
            "🎬 Endi kino kodini yuboring."
        )

        await callback.answer()

    else:

        await callback.answer(
            "❌ Hali kanalga obuna bo‘lmagansiz!",
            show_alert=True
        )


# =========================
# ADMIN: KINO QO‘SHISH
# =========================

@dp.message_handler(commands=["save"])
async def save_movie(
    message: types.Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "❌ Siz admin emassiz."
        )

        return

    text = message.text.replace(
        "/save",
        "",
        1
    ).strip()

    if "|" not in text:

        await message.answer(
            "❌ To‘g‘ri format:\n\n"
            "/save 123 | Kino nomi"
        )

        return

    code, title = text.split(
        "|",
        1
    )

    code = code.strip()
    title = title.strip()

    if not code or not title:

        await message.answer(
            "❌ Kod yoki kino nomi bo‘sh."
        )

        return

    await state.update_data(
        code=code,
        title=title
    )

    await MovieState.waiting_video.set()

    await message.answer(
        "🎬 Kino ma’lumotlari qabul qilindi.\n\n"
        f"🔢 Kod: <b>{code}</b>\n"
        f"🎞 Nomi: <b>{title}</b>\n\n"
        "Endi shu yerga videoni yuboring."
    )


# =========================
# ADMIN: VIDEO QABUL QILISH
# =========================

@dp.message_handler(
    content_types=types.ContentType.VIDEO,
    state=MovieState.waiting_video
)
async def receive_video(
    message: types.Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:

        await state.finish()

        return

    data = await state.get_data()

    code = data.get("code")
    title = data.get("title")

    file_id = message.video.file_id

    cursor.execute(
        """
        INSERT OR REPLACE INTO movies
        (code, title, file_id)
        VALUES (?, ?, ?)
        """,
        (
            code,
            title,
            file_id
        )
    )

    conn.commit()

    await state.finish()

    await message.answer(
        "✅ <b>Kino saqlandi!</b>\n\n"
        f"🔢 Kod: <b>{code}</b>\n"
        f"🎬 Nomi: <b>{title}</b>"
    )


# =========================
# ADMIN: KINOLAR RO‘YXATI
# =========================

@dp.message_handler(commands=["list"])
async def movie_list(message: types.Message):

    if message.from_user.id != ADMIN_ID:

        return

    cursor.execute(
        "SELECT code, title FROM movies ORDER BY code"
    )

    movies = cursor.fetchall()

    if not movies:

        await message.answer(
            "📂 Hozircha kino yo‘q."
        )

        return

    text = "🎬 <b>Kinolar:</b>\n\n"

    for code, title in movies:

        text += (
            f"🔢 <b>{code}</b> — "
            f"{title}\n"
        )

    await message.answer(text)


# =========================
# ADMIN: KINO O‘CHIRISH
# =========================

@dp.message_handler(commands=["delete"])
async def delete_movie(message: types.Message):

    if message.from_user.id != ADMIN_ID:

        return

    code = message.text.replace(
        "/delete",
        "",
        1
    ).strip()

    if not code:

        await message.answer(
            "❌ Format:\n"
            "/delete 123"
        )

        return

    cursor.execute(
        "DELETE FROM movies WHERE code = ?",
        (code,)
    )

    conn.commit()

    if cursor.rowcount == 0:

        await message.answer(
            "❌ Bunday kodli kino topilmadi."
        )

    else:

        await message.answer(
            f"✅ <b>{code}</b> kodli kino o‘chirildi."
        )


# =========================
# KINO KODINI QIDIRISH
# =========================

@dp.message_handler(
    content_types=types.ContentType.TEXT
)
async def find_movie(message: types.Message):

    # Admin buyruqlarini o'tkazib yuboramiz
    if message.text.startswith("/"):

        return

    subscribed = await check_subscription(
        message.from_user.id
    )

    if not subscribed:

        await message.answer(
            "❌ Avval kanalga obuna bo‘ling:",
            reply_markup=subscription_keyboard()
        )

        return

    code = message.text.strip()

    cursor.execute(
        """
        SELECT title, file_id
        FROM movies
        WHERE code = ?
        """,
        (code,)
    )

    movie = cursor.fetchone()

    if not movie:

        await message.answer(
            "❌ Bu kod bo‘yicha kino topilmadi."
        )

        return

    title, file_id = movie

    await message.answer_video(
        video=file_id,
        caption=f"🎬 <b>{title}</b>"
    )


# =========================
# ISHGA TUSHIRISH
# =========================

if __name__ == "__main__":

    print("🎬 Kino bot ishga tushdi...")

    executor.start_polling(
        dp,
        skip_updates=True
    )
