import os
import json
import asyncio
import genshin
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from datetime import datetime
import humanize

# معلومات البوت (من متغيرات البيئة)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

# اسم ملف البيانات
USERS_DATA_FILE = 'users_data.json'

# دالة لتحميل بيانات المستخدمين من ملف JSON
def load_users_data():
    if os.path.exists(USERS_DATA_FILE) and os.stat(USERS_DATA_FILE).st_size != 0:
        with open(USERS_DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# دالة لحفظ بيانات المستخدمين في ملف JSON
def save_users_data(data):
    with open(USERS_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# تهيئة البوت
bot = TelegramClient('genshin_multi_user_session', API_ID, API_HASH)

# دالة مساعدة لإنشاء عميل genshin.py لكل مستخدم
def get_genshin_client(user_id):
    users_data = load_users_data()
    if user_id not in users_data:
        return None, None, None
    
    ltuid_v2 = users_data[user_id]['ltuid_v2']
    ltoken_v2 = users_data[user_id]['ltoken_v2']
    in_game_uid = users_data[user_id]['uid']
    
    client = genshin.Client({"ltuid_v2": ltuid_v2, "ltoken_v2": ltoken_v2})
    return client, ltuid_v2, in_game_uid

# ----- الأوامر العامة -----

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    message = (
        "أهلاً بك في بوت إحصائيات Genshin Impact! 🤖\n\n"
        "للبدء، يرجى ربط حسابك عن طريق إرسال ملفات تعريف الارتباط (Cookies) الخاصة بك والـUID في محادثة خاصة معي.\n\n"
        "**الأمر:** `/setcookies <ltuid_v2> <ltoken_v2> <uid>`\n\n"
        "**تنبيه:** هذا الأمر يعمل فقط في محادثة خاصة لضمان أمان بياناتك."
    )
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/setcookies'))
async def setcookies_handler(event):
    if not event.is_private:
        await event.reply("❌ هذا الأمر متاح فقط في محادثة خاصة لضمان أمان بياناتك.")
        return

    command_parts = event.text.split(' ', 3)
    if len(command_parts) < 4:
        await event.respond("❌ يرجى إدخال ltuid_v2 و ltoken_v2 والـUID.\n\n"
                            "**مثال:** `/setcookies 123456789 aBcDeFg 726339362`")
        return
    
    try:
        ltuid_v2 = int(command_parts[1])
        ltoken_v2 = command_parts[2]
        in_game_uid = int(command_parts[3])
        user_id = str(event.sender_id)

        users_data = load_users_data()
        users_data[user_id] = {'ltuid_v2': ltuid_v2, 'ltoken_v2': ltoken_v2, 'uid': in_game_uid}
        save_users_data(users_data)
        
        await event.respond("✅ تم حفظ بيانات حسابك بنجاح! يمكنك الآن استخدام الأوامر الأخرى.")
    except ValueError:
        await event.respond("❌ خطأ: تأكد من أن ltuid_v2 والـUID هما رقمان صحيحان.")
    except Exception as e:
        await event.respond(f"❌ حدث خطأ أثناء حفظ البيانات: {e}")

# ----- أوامر الإحصائيات العامة -----

@bot.on(events.NewMessage(pattern='/stats'))
async def stats_handler(event):
    user_id = str(event.sender_id)
    client, _, uid = get_genshin_client(user_id)
    
    if not client:
        await event.respond("❌ لم يتم ربط حسابك بعد. يرجى استخدام أمر `/setcookies` في محادثة خاصة معي أولاً.")
        return

    await event.respond("جارٍ جلب إحصائيات حسابك من HoYoLAB، يرجى الانتظار...")
    
    try:
        notes = await client.get_notes(uid=uid)
        
        message = (
            f"**📊 إحصائيات HoYoLAB:**\n"
            f"💧 **الريزن الأصلي:** {notes.current_resin}/{notes.max_resin}\n"
            f"⏰ **متبقي لاستعادة الريزن:** {humanize.naturaltime(notes.resin_recovery_time)}\n"
            f"📦 **مهمات اليوم:** {notes.completed_commissions}/{notes.max_commissions}\n"
            f"✨ **قوة الكاوشيوم الأسبوعية:** {notes.current_weekly_boss_resin}/{notes.max_weekly_boss_resin}\n"
            f"🗺️ **البعثات:** {notes.completed_expeditions}/{notes.max_expeditions}"
        )
        
        await event.respond(message)
    
    except genshin.errors.InvalidCookies:
        await event.respond("❌ خطأ: ملفات تعريف الارتباط (Cookies) الخاصة بك غير صالحة. يرجى تحديثها باستخدام `/setcookies`.")
    except Exception as e:
        await event.respond(f"❌ حدث خطأ غير متوقع: {e}")

# ----- أمر جلب معلومات الـSpiral Abyss -----

@bot.on(events.NewMessage(pattern='/abyss'))
async def abyss_handler(event):
    user_id = str(event.sender_id)
    client, _, uid = get_genshin_client(user_id)
    
    if not client:
        await event.respond("❌ لم يتم ربط حسابك بعد. يرجى استخدام أمر `/setcookies` في محادثة خاصة معي أولاً.")
        return

    await event.respond("جارٍ جلب إحصائيات الـSpiral Abyss...")
    
    try:
        abyss = await client.get_spiral_abyss(uid=uid)
        
        message = (
            f"**⚔️ إحصائيات الـSpiral Abyss (الدورة الحالية):**\n"
            f"✨ **الدور المكتمل:** {abyss.total_battles}\n"
            f"⭐ **النجوم المكتسبة:** {abyss.total_stars}\n"
            f"👑 **أعلى فوز:** {abyss.most_played_characters[0].name} ({abyss.most_played_characters[0].value} مرات)"
        )
        
        await event.respond(message)
    
    except genshin.errors.InvalidCookies:
        await event.respond("❌ خطأ: ملفات تعريف الارتباط (Cookies) الخاصة بك غير صالحة. يرجى تحديثها باستخدام `/setcookies`.")
    except Exception as e:
        await event.respond(f"❌ حدث خطأ غير متوقع: {e}")

# ----- أمر تسجيل الدخول اليومي -----

@bot.on(events.NewMessage(pattern='/checkin'))
async def checkin_handler(event):
    user_id = str(event.sender_id)
    client, _, uid = get_genshin_client(user_id)
    
    if not client:
        await event.respond("❌ لم يتم ربط حسابك بعد. يرجى استخدام أمر `/setcookies` في محادثة خاصة معي أولاً.")
        return

    await event.respond("جارٍ تسجيل الدخول اليومي...")
    
    try:
        reward = await client.claim_daily_reward()
        message = (
            f"🎁 **تم تسجيل الدخول بنجاح!**\n"
            f"لقد حصلت على: {reward.amount}x {reward.name}\n"
            f"لقد قمت بتسجيل الدخول لـ **{reward.day}** يومًا هذا الشهر."
        )
        await event.respond(message)
    
    except genshin.errors.AlreadyClaimed:
        await event.respond("✅ لقد قمت بتسجيل الدخول اليوم بالفعل!")
    except genshin.errors.InvalidCookies:
        await event.respond("❌ خطأ: ملفات تعريف الارتباط (Cookies) الخاصة بك غير صالحة. يرجى تحديثها باستخدام `/setcookies`.")
    except Exception as e:
        await event.respond(f"❌ حدث خطأ غير متوقع: {e}")

# ----- أمر جلب قائمة الشخصيات في واجهة العرض -----

@bot.on(events.NewMessage(pattern='/showcase'))
async def showcase_handler(event):
    user_id = str(event.sender_id)
    client, _, uid = get_genshin_client(user_id)

    if not client:
        await event.respond("❌ لم يتم ربط حسابك بعد. يرجى استخدام أمر `/setcookies` في محادثة خاصة معي أولاً.")
        return

    await event.respond("جارٍ جلب الشخصيات من واجهة العرض الخاصة بك...")

    try:
        characters = await client.get_characters(uid=uid)
        
        if not characters:
            await event.respond("❌ لا توجد شخصيات في واجهة العرض. تأكد من أن حسابك عام وأن لديك شخصيات معروضة.")
            return
        
        character_names = [char.name for char in characters]
        message = (
            f"**👤 شخصياتك في واجهة العرض:**\n"
            f"{', '.join(character_names)}"
        )
        await event.respond(message)

    except genshin.errors.DataNotPublic:
        await event.respond("❌ خطأ: ملفك الشخصي ليس عامًا. يرجى التأكد من أن إعدادات العرض في اللعبة عامة.")
    except genshin.errors.InvalidCookies:
        await event.respond("❌ خطأ: ملفات تعريف الارتباط (Cookies) الخاصة بك غير صالحة. يرجى تحديثها باستخدام `/setcookies`.")
    except Exception as e:
        await event.respond(f"❌ حدث خطأ غير متوقع: {e}")

# ----- أمر جلب ملخص أرباح Primogems و Mora (الدفتر اليومي) -----

@bot.on(events.NewMessage(pattern='/diary'))
async def diary_handler(event):
    user_id = str(event.sender_id)
    client, _, uid = get_genshin_client(user_id)

    if not client:
        await event.respond("❌ لم يتم ربط حسابك بعد. يرجى استخدام أمر `/setcookies` في محادثة خاصة معي أولاً.")
        return
    
    await event.respond("جارٍ جلب ملخص الدفتر اليومي...")

    try:
        diary = await client.get_diary(uid=uid)
        
        message = (
            f"**💰 ملخص الدفتر اليومي (شهر {diary.month}):**\n"
            f"💎 **Primogems هذا الشهر:** {diary.data.primogems}\n"
            f"💵 **Mora هذا الشهر:** {diary.data.mora}"
        )
        await event.respond(message)

    except genshin.errors.InvalidCookies:
        await event.respond("❌ خطأ: ملفات تعريف الارتباط (Cookies) الخاصة بك غير صالحة. يرجى تحديثها باستخدام `/setcookies`.")
    except Exception as e:
        await event.respond(f"❌ حدث خطأ غير متوقع: {e}")

async def main():
    print("[✓] البوت يعمل...")
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == "__main__":
    if not BOT_TOKEN or not API_ID or not API_HASH:
        print("[!] خطأ: متغيرات البيئة BOT_TOKEN, API_ID, أو API_HASH غير موجودة.")
    else:
        asyncio.run(main())
