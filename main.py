import asyncio
import logging
import os # <-- إضافة جديدة لاستخدام متغيرات البيئة
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from enka import EnkaClient

# إعداد تسجيل الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# قراءة التوكن من متغيرات البيئة
# سنقوم بتعيين هذا المتغير لاحقًا في لوحة تحكم Koyeb
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("لم يتم العثور على متغير البيئة TELEGRAM_BOT_TOKEN. يرجى تعيينه.")

# ... (بقية الدوال start و showcase تبقى كما هي بدون تغيير) ...
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال رسالة ترحيبية عند إرسال الأمر /start."""
    welcome_message = (
        "أهلاً بك في بوت عرض شخصيات Enka!\n\n"
        "استخدم الأمر `/showcase <UID>` لعرض بيانات لاعب.\n\n"
        "مثال:\n"
        "`/showcase 800000000`"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def showcase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """جلب وعرض بيانات شخصيات اللاعب باستخدام UID."""
    if not context.args:
        await update.message.reply_text("الرجاء إدخال UID بعد الأمر.\nمثال: `/showcase 800000000`")
        return

    uid = context.args[0]
    
    if not uid.isdigit():
        await update.message.reply_text("الـ UID يجب أن يكون رقمًا.")
        return

    processing_message = await update.message.reply_text("جاري جلب البيانات من Enka.network، يرجى الانتظار... ⌛")

    try:
        async with EnkaClient(lang="ar") as client:
            user_data = await client.fetch_user(uid)

            if not user_data.characters:
                await processing_message.edit_text(f"لم يتم العثور على شخصيات في واجهة العرض للـ UID: {uid}\n\nتأكد من:\n1. أن الـ UID صحيح.\n2. أن اللاعب قام بوضع شخصياته في الـ 'Character Showcase' داخل اللعبة.\n3. أن خيار 'Show Character Details' مفعل.")
                return

            player_info = f"👤 **معلومات اللاعب:**\n- **الاسم:** {user_data.player.nickname}\n- **المستوى:** {user_data.player.level}\n- **عالم المستوى:** {user_data.player.world_level}\n\n"
            
            characters_info = "✨ **الشخصيات المعروضة:**\n" + ("-"*20) + "\n"

            for char in user_data.characters:
                weapon = char.weapon
                artifacts = char.artifacts
                
                characters_info += f"**{char.name}** (لفل {char.level})\n"
                characters_info += f"⚔️ **السلاح:** {weapon.name} (لفل {weapon.level})\n"
                characters_info += f"🌼 **الآرتيفاكتات:** {len(artifacts)} قطع\n\n"

            await processing_message.edit_text(player_info + characters_info)

    except Exception as e:
        logger.error(f"حدث خطأ عند جلب بيانات UID {uid}: {e}")
        await processing_message.edit_text(f"حدث خطأ غير متوقع عند محاولة جلب البيانات للـ UID: {uid}.\nالرجاء المحاولة مرة أخرى لاحقًا أو التأكد من صحة الـ UID.")


def main() -> None:
    """بدء تشغيل البوت."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("showcase", showcase))

    # بدء تشغيل البوت والاستماع للطلبات
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
