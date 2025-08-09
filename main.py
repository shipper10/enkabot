import os
import json
import asyncio
import requests
from bs4 import BeautifulSoup
from telethon import TelegramClient, events, Button
from telethon.tl.types import ChatBannedRights
from telethon.errors import FloodWaitError

# معلومات البوت (يجب أن يتم تزويدها كمتغيرات بيئية على Koyeb)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

# اسم ملف الجلسة والبيانات
SESSION_NAME = 'akasha_bot_session'
USERS_DATA_FILE = 'users_data.json'

# القواميس الخاصة بالألعاب (تم التحديث ل Akasha.cv)
GAMES_CONFIG = {
    'gen': {
        'name': 'Genshin Impact',
        'url_template': "https://akasha.cv/profile/{uid}/",
        'setuid_command': '/setuid_gen'
    },
    'hsr': {
        'name': 'Honkai: Star Rail',
        'url_template': "https://akasha.cv/profile/{uid}/",
        'setuid_command': '/setuid_hsr'
    }
}

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

# دالة لجلب أسماء الشخصيات وصورها من ملف Akasha.cv
def fetch_akasha_data(game_key, uid):
    print(f"[*] جلب بيانات الملف الشخصي لـUID: {uid} من لعبة {GAMES_CONFIG[game_key]['name']}...")
    try:
        profile_url = GAMES_CONFIG[game_key]['url_template'].format(uid=uid)
        response = requests.get(profile_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        characters_data = {}
        # البحث عن عناصر الشخصيات في الصفحة
        for char_div in soup.find_all('div', class_='character-card'):
            char_name_div = char_div.find('h4', class_='character-card-name')
            char_img = char_div.find('img', class_='character-image')
            
            if char_name_div and char_img:
                character_name = char_name_div.text.strip()
                image_url = char_img['src']
                characters_data[character_name] = image_url
        
        return characters_data

    except requests.exceptions.RequestException as e:
        print(f"[!] خطأ في جلب بيانات الملف الشخصي: {e}")
        return None
    except Exception as e:
        print(f"[!] خطأ في تحليل HTML: {e}")
        return None

# تهيئة البوت باستخدام ملف الجلسة
bot = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ----- أوامر البوت -----

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    message = (
        "أهلاً بك في بوت Akasha! 🤖\n"
        "لاستخدام البوت، قم أولاً بتعيين UID لكل لعبة:\n"
        "`/setuid_gen <uid>` (Genshin Impact)\n"
        "`/setuid_hsr <uid>` (Honkai: Star Rail)\n\n"
        "بعدها، يمكنك:\n"
        "1. إرسال اسم الشخصية مع الأمر الخاص باللعبة:\n"
        "`/gen Eula`\n"
        "2. أو عرض الشخصيات المتوفرة في ملفك الشخصي كأزرار:\n"
        "`/characters gen`"
    )
    await event.respond(message)

# أمر لتعيين UID لكل لعبة
@bot.on(events.NewMessage(pattern='/(setuid_gen|setuid_hsr)'))
async def setuid_handler(event):
    command_parts = event.text.split(' ', 1)
    command = command_parts[0].lstrip('/')
    uid_str = command_parts[1].strip() if len(command_parts) > 1 else ''
    
    game_key = command.split('_')[1]
    
    users_data = load_users_data()
    user_id = str(event.sender_id)
    
    if user_id not in users_data:
        users_data[user_id] = {}

    if uid_str.isdigit() and len(uid_str) in [9, 10]:
        users_data[user_id][game_key] = uid_str
        save_users_data(users_data)
        await event.respond(f"تم حفظ UID الخاص بـ {GAMES_CONFIG[game_key]['name']}: `{uid_str}`")
    else:
        await event.respond(f"يرجى إدخال UID صحيح. مثال: `{GAMES_CONFIG[game_key]['setuid_command']} 123456789`")

# أمر لعرض الشخصيات على شكل أزرار
@bot.on(events.NewMessage(pattern='/characters'))
async def show_characters_handler(event):
    command_parts = event.text.split(' ', 1)
    if len(command_parts) < 2:
        await event.respond("يرجى تحديد اللعبة.\nمثال: `/characters gen`")
        return
    
    game_key = command_parts[1].strip().lower()
    
    if game_key not in GAMES_CONFIG:
        await event.respond("اللعبة غير مدعومة. الألعاب المدعومة هي: gen, hsr")
        return
    
    user_id = str(event.sender_id)
    users_data = load_users_data()
    
    if user_id not in users_data or game_key not in users_data[user_id]:
        await event.respond(f"لم يتم تعيين UID للعبة {GAMES_CONFIG[game_key]['name']} بعد. يرجى استخدام أمر `{GAMES_CONFIG[game_key]['setuid_command']}` أولاً.")
        return
    
    uid = users_data[user_id][game_key]
    await event.respond("جارٍ جلب الشخصيات المتوفرة في ملفك الشخصي على Akasha.cv...")
    
    available_characters = fetch_akasha_data(game_key, uid)
    
    if not available_characters:
        await event.respond(f"لا توجد شخصيات متاحة في ملفك الشخصي على Akasha.cv لـUID `{uid}`. تأكد من أن ملفك الشخصي تم تحديثه بنجاح.")
        return
    
    # إنشاء الأزرار
    buttons = []
    for i in range(0, len(available_characters), 3):
        row = []
        for char_name in list(available_characters.keys())[i:i+3]:
            row.append(Button.inline(char_name, f"character_{game_key}_{char_name}"))
        buttons.append(row)
        
    await bot.send_message(
        event.chat_id,
        f"اختر شخصية من لعبة {GAMES_CONFIG[game_key]['name']} (المتوفرة حالياً):",
        buttons=buttons
    )

# أمر لجلب الشخصية من خلال كتابة اسمها
@bot.on(events.NewMessage(pattern='/(gen|hsr)'))
async def character_handler_text(event):
    command_parts = event.text.split(' ', 1)
    if len(command_parts) < 2:
        await event.respond(f"يرجى إدخال اسم الشخصية بعد الأمر.")
        return
    
    game_key = command_parts[0].lstrip('/')
    character_name = command_parts[1].strip()
    
    user_id = str(event.sender_id)
    users_data = load_users_data()
    
    if user_id not in users_data or game_key not in users_data[user_id]:
        await event.respond(f"لم يتم تعيين UID للعبة {GAMES_CONFIG[game_key]['name']} بعد. يرجى استخدام أمر `{GAMES_CONFIG[game_key]['setuid_command']}` أولاً.")
        return

    uid = users_data[user_id][game_key]
    
    await event.respond("جارٍ البحث عن الشخصية، يرجى الانتظار...")
    
    characters_data = fetch_akasha_data(game_key, uid)
    if not characters_data or character_name not in characters_data:
        await event.respond(f"لم يتم العثور على الشخصية '{character_name}' في ملفك الشخصي على Akasha.cv.")
        return

    image_url = characters_data[character_name]
    
    try:
        await event.respond(file=image_url)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
        await event.respond(file=image_url)
    except Exception as e:
        await event.respond(f"حدث خطأ أثناء إرسال الصورة: {e}")


# معالج الأزرار
@bot.on(events.CallbackQuery())
async def button_handler(event):
    data_str = event.data.decode('utf-8')
    if data_str.startswith('character_'):
        parts = data_str.split('_')
        game_key = parts[1]
        character_name = parts[2]
        
        user_id = str(event.sender_id)
        users_data = load_users_data()
        
        if user_id not in users_data or game_key not in users_data[user_id]:
            await event.respond(f"لم يتم تعيين UID للعبة {GAMES_CONFIG[game_key]['name']} بعد. يرجى استخدام أمر `{GAMES_CONFIG[game_key]['setuid_command']}` أولاً.", alert=True)
            return

        uid = users_data[user_id][game_key]
        
        await bot.edit_message(event.chat_id, event.message_id, "جارٍ البحث عن الشخصية...")
        
        characters_data = fetch_akasha_data(game_key, uid)
        if not characters_data or character_name not in characters_data:
            await bot.edit_message(event.chat_id, event.message_id,
                f"لم يتم العثور على الشخصية '{character_name}' في ملفك الشخصي على Akasha.cv."
            )
            return

        image_url = characters_data[character_name]
        
        try:
            await bot.send_file(event.chat_id, file=image_url)
            await event.delete()
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            await bot.send_file(event.chat_id, file=image_url)
            await event.delete()
        except Exception as e:
            await bot.edit_message(event.chat_id, event.message_id, f"حدث خطأ أثناء إرسال الصورة: {e}")

async def main():
    print("[✓] البوت يعمل...")
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == "__main__":
    if not BOT_TOKEN or not API_ID or not API_HASH:
        print("[!] خطأ: متغيرات البيئة BOT_TOKEN, API_ID, أو API_HASH غير موجودة.")
    else:
        asyncio.run(main())
