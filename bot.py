import subprocess
import sys
import os
import logging

# ===== تثبيت المكتبات من GitHub وقت التشغيل =====
pkgs = [
    "git+https://github.com/mrwan200/enkanetwork.git",
    "git+https://github.com/Veliani/EnkaNetworkCard.git"
]
for pkg in pkgs:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
    except Exception as e:
        print(f"❌ فشل تثبيت {pkg}: {e}")
        sys.exit(1)

# ===== بعد التثبيت استيراد المكتبات =====
from telegram.ext import ApplicationBuilder, CommandHandler
import enkanetwork as enka
from enkacard import generate_card
from io import BytesIO

# ===== إعدادات البوت =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ لم يتم تحديد BOT_TOKEN في متغيرات البيئة")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
client = enka.EnkaNetworkAPI(lang=enka.Language.EN)

# ===== أوامر البوت =====
async def start(update, context):
    await update.message.reply_text("Hello! Send /stats <UID> to get Genshin Impact stats.")

async def stats(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /stats <UID>")
        return

    uid = context.args[0]
    try:
        data = await client.fetch_user(uid)
        card = await generate_card(data)  # توليد البطاقة
        buf = BytesIO()
        card.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(buf)
    except Exception as e:
        await update.message.reply_text(f"Error fetching stats: {e}")

# ===== تشغيل البوت =====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))

if __name__ == "__main__":
    app.run_polling()
