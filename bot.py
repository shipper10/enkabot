import telebot
from enkanetwork import EnkaNetworkAPI
from enkacard import EnkaCard, enc_enums

# ضع التوكن الخاص بالبوت هنا
TOKEN = "توكن_البوت_الخاص_بك"

# قم بإنشاء كائن (instance) للبوت
bot = telebot.TeleBot(TOKEN)

# قم بإنشاء كائن (instance) لمكتبة EnkaNetwork
enka_api = EnkaNetworkAPI()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """
    يرسل رسالة ترحيبية عند استخدام الأمر /start أو /help.
    """
    bot.send_message(message.chat.id, "أهلاً بك! أرسل لي رقم UID الخاص بك وسأرسل لك بطاقة شخصياتك في Genshin Impact.")

@bot.message_handler(func=lambda message: message.text.isdigit() and len(message.text) == 9)
def handle_uid(message):
    """
    يتعامل مع الأرقام المرسلة ويتحقق منها.
    إذا كانت رقم UID صالح، يقوم بإنشاء البطاقة.
    """
    uid = int(message.text)
    chat_id = message.chat.id
    
    # إعلام المستخدم أن البوت يعمل على طلبهم
    bot.send_message(chat_id, "جاري استخراج البيانات، يرجى الانتظار...")

    try:
        # استخدام مكتبة EnkaNetwork للحصول على بيانات اللاعب
        player_info = enka_api.fetch_user_by_uid(uid)
        
        # استخدام مكتبة EnkaCard لإنشاء البطاقة
        enkacard = EnkaCard(player_info)
        
        # إنشاء الصورة النهائية
        card = enkacard.create()
        
        # إرسال الصورة إلى المستخدم
        bot.send_photo(chat_id, card)
        
    except Exception as e:
        # في حالة حدوث خطأ
        bot.send_message(chat_id, f"عذرًا، حدث خطأ: {e}\nتأكد من أن رقم الـ UID صحيح وأن ملفك الشخصي عام في لعبة Genshin Impact.")

# تشغيل البوت
bot.polling()
