import os
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from dotenv import load_dotenv
import nest_asyncio
import asyncio

# .env fayldan tokenni yuklaymiz
load_dotenv()
TOKEN = os.getenv("8060933538:AAEs8l0PxrwoeIJSVjtGlEva0UE81d_T_DU")

# Bosqichlar
TIL, TOVAR, NARX = range(3)

# Foydalanuvchini CSV faylda saqlash
def save_user_id(user_id):
    if os.path.exists("users.csv"):
        users_df = pd.read_csv("users.csv")
    else:
        users_df = pd.DataFrame(columns=["user_id"])

    if user_id not in users_df["user_id"].values:
        users_df.loc[len(users_df)] = [user_id]
        users_df.to_csv("users.csv", index=False)

# Xarajatni yozish
def log_expense(user_id, product, price):
    file = "expenses.csv"
    now = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(file):
        df = pd.read_csv(file)
    else:
        df = pd.DataFrame(columns=["user_id", "date", "product", "price"])
    df.loc[len(df)] = [user_id, now, product, price]
    df.to_csv(file, index=False)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    save_user_id(user_id)
    keyboard = [[KeyboardButton("🇺🇿 O'zbek"), KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Tilni tanlang / Выберите язык / Choose your language:", reply_markup=reply_markup)
    return TIL

# Tilni tanlash
async def tilni_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    til = update.message.text
    if "Рус" in til:
        context.user_data["til"] = "rus"
        msg = "👋 Привет! Введите название товара."
        button = "🌀 ИЗМЕНИТЬ ЯЗЫК"
    elif "English" in til:
        context.user_data["til"] = "eng"
        msg = "👋 Hi! Please enter the product name."
        button = "🌀 CHANGE LANGUAGE"
    else:
        context.user_data["til"] = "uzb"
        msg = "👋 Salom! Tovar nomini yozing."
        button = "🌀 TILNI ALMASHTIRISH"
    keyboard = [[button]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return TOVAR

# Tovar nomini olish
async def tovar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if "ЯЗЫК" in text or "TILNI" in text or "LANGUAGE" in text:
        return await change_language(update, context)
    context.user_data["tovar"] = text
    til = context.user_data.get("til", "uzb")
    msg = {
        "rus": "Теперь введите цену товара:",
        "uzb": "Endi tovarning narxini kiriting:",
        "eng": "Now enter the price of the product:"
    }
    await update.message.reply_text(msg[til])
    return NARX

# Narxni olish
async def narx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    til = context.user_data.get("til", "uzb")
    if "ЯЗЫК" in text or "TILNI" in text or "LANGUAGE" in text:
        return await change_language(update, context)
    try:
        narx = float(text)
    except ValueError:
        msg = {
            "rus": "Неверный формат. Введите число.",
            "uzb": "Narxni noto'g'ri kiritdingiz. Iltimos, raqam kiriting.",
            "eng": "Invalid input. Please enter a number."
        }
        await update.message.reply_text(msg[til])
        return NARX
    tovar = context.user_data.get("tovar")
    context.user_data["hisob"] = context.user_data.get("hisob", 0) + narx
    log_expense(update.message.from_user.id, tovar, narx)
    javob = {
        "rus": f"Товар: {tovar}\nЦена: {narx} сум\nОбщий счет: {context.user_data['hisob']} сум\nВведите название следующего товара:",
        "uzb": f"Tovar: {tovar}\nNarx: {narx} so'm\nUmumiy hisob: {context.user_data['hisob']} so'm\nYangi tovar nomini kiriting:",
        "eng": f"Product: {tovar}\nPrice: {narx} UZS\nTotal: {context.user_data['hisob']} UZS\nEnter next product name:"
    }
    await update.message.reply_text(javob[til])
    return TOVAR

# /hisob
async def hisob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = context.user_data.get("hisob", 0)
    til = context.user_data.get("til", "uzb")
    msg = {
        "rus": f"Общий счет: {total} сум",
        "uzb": f"Umumiy hisob: {total} so'm",
        "eng": f"Total: {total} UZS"
    }
    await update.message.reply_text(msg[til])

# /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hisob"] = 0
    til = context.user_data.get("til", "uzb")
    msg = {
        "rus": "Общий счет сброшен.",
        "uzb": "Hisob nolga tushirildi.",
        "eng": "Total has been reset to zero."
    }
    await update.message.reply_text(msg[til])

# /jadval
async def jadval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    til = context.user_data.get("til", "uzb")
    now_month = datetime.now().strftime("%Y-%m")
    try:
        df = pd.read_csv("expenses.csv")
        df = df[(df["user_id"] == user_id) & (df["date"].str.startswith(now_month))]
    except:
        df = pd.DataFrame()
    if df.empty:
        msg = {
            "rus": "В этом месяце расходов нет.",
            "uzb": "Bu oyda hech qanday xarajat qilinmagan.",
            "eng": "No expenses this month."
        }
        await update.message.reply_text(msg[til])
    else:
        text = ""
        for _, row in df.iterrows():
            text += f"{row['date']} - {row['product']} - {row['price']} so'm\n"
        total = df["price"].sum()
        javob = {
            "rus": f"🗓️ Расходы за месяц:\n{text}\nИтого: {total} сум",
            "uzb": f"🗓️ Oylik xarajatlar:\n{text}\nJami: {total} so'm",
            "eng": f"🗓️ Monthly expenses:\n{text}\nTotal: {total} UZS"
        }
        await update.message.reply_text(javob[til])

# Tilni o'zgartirish
async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[KeyboardButton("🇺🇿 O'zbek"), KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Tilni tanlang / Выберите язык / Choose language:", reply_markup=reply_markup)
    return TIL

# Main funksiyasi
async def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, tilni_tanlash)],
            TOVAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, tovar)],
            NARX: [MessageHandler(filters.TEXT & ~filters.COMMAND, narx)],
        },
        fallbacks=[CommandHandler("hisob", hisob)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("hisob", hisob))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("jadval", jadval))

    await application.run_polling()

# Colab / Render uchun asyncio patch
nest_asyncio.apply()
asyncio.get_event_loop().run_until_complete(main())
