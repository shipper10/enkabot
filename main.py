import os
import json
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.types import ChatBannedRights
from telethon.errors import FloodWaitError
import requests

# معلومات البوت (يجب أن يتم تزويدها كمتغيرات بيئية على Koyeb)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

# اسم ملف الجلسة والبيانات
SESSION_NAME = 'enka_bot_session'
USERS_DATA_FILE = 'users_data.json'

# القواميس الخاصة بالألعاب
GAMES_CONFIG = {
    'gen': {
        'name': 'Genshin Impact',
        'api_url': "https://enka.network/api/uid/{uid}/",
        'setuid_command': '/setuid_gen',
        'image_base_url': "https://enka.network/ui/"
    },
    'hsr': {
        'name': 'Honkai: Star Rail',
        'api_url': "https://enka.network/api/hsr/uid/{uid}/",
        'setuid_command': '/setuid_hsr',
        'image_base_url': "https://enka.network/ui/"
    },
    'zzz': {
        'name': 'Zenless Zone Zero',
        'api_url': "https://enka.network/api/zzz/uid/{uid}/",
        'setuid_command': '/setuid_zzz',
        'image_base_url': "https://enka.network/ui/"
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

# -------------------------------------------------------------
# الدالة التالية هي التي تم تعديلها لإضافة أوامر الطباعة (print)
# -------------------------------------------------------------
def fetch_enka_api_data(game_key, uid):
    print(f"[*] جلب بيانات الملف الشخصي لـUID: {uid} من لعبة {GAMES_CONFIG[game_key]['name']} باستخدام الـAPI...")
    
    api_url = GAMES_CONFIG[game_key]['api_url'].format(uid=uid)
    print(f"[*] الرابط المستخدم: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=15)
        print(f"[*] حالة استجابة الـAPI: {response.status_code}")
        
        response.raise_for_status() # إظهار خطأ إذا لم تكن الحالة 200
        
        data = response.json()
        print("[*] تم استلام بيانات JSON بنجاح.")
        
        characters_data = {}
        if 'avatarInfoList' in data:
            for char_info in data['avatarInfoList']:
                char_name = char_info.get('nameTextMapHash') 
                char_icon = char_info.get('image', {}).get('icon') 

                if char_name and char_icon:
                    # بناء رابط الصورة الكامل
                    image_url = GAMES_CONFIG[game_key]['image_base_url'] + char_icon
                    characters_data[char_name] = image_url
        
        print(f"[*] تم العثور على الشخصيات التالية: {list(characters_data.keys())}")
        
        if not characters_data:
            print("[!] لم يتم العثور على أي شخصيات في البيانات المستلمة.")
            
        return characters_data
    
    except requests.exceptions.HTTPError as e:
        print(f"[!] خطأ في الـAPI (استجابة HTTP غير ناجحة): {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[!] خطأ في الاتصال بالـAPI: {e}")
        return None
    except Exception as e:
        print(f"[!] خطأ في معالجة البيانات: {e}")
        return None
# -------------------------------------------------------------
# نهاية الدالة المعدلة
# -------------------------------------------------------------

# تهيئة البوت باستخدام ملف الجلسة
bot = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ----- أوامر البوت -----

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    message = (
        "أهلاً بك في بوت Enka! 🤖\n"
        "لاستخدام البوت، قم أولاً بتعيين UID لكل لعبة:\n"
        "`/setuid_gen <uid>` (Genshin Impact)\n"
        "`/setuid_hsr <uid>` (Honkai: Star Rail)\n"
        "`/setuid_zzz <uid>` (Zenless Zone Zero)\n\n"
        "بعدها، يمكنك:\n"
        "1. إرسال اسم الشخصية مع الأمر الخاص باللعبة:\n"
        "`/gen Eula`\n"
        "2. أو عرض الشخصيات المتوفرة في واجهة العرض كأزرار:\n"
        "`/characters gen`"
    )
    await event.respond(message)

# أمر لتعيين UID لكل لعبة
@bot.on(events.NewMessage(pattern='/(setuid_gen|setuid_hsr|setuid_zzz)'))
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
        await event.respond("اللعبة غير مدعومة. الألعاب المدعومة هي: gen, hsr, zzz")
        return
    
    user_id = str(event.sender_id)
    users_data = load_users_data()
    
    if user_id not in users_data or game_key not in users_data[user_id]:
        await event.respond(f"لم يتم تعيين UID للعبة {GAMES_CONFIG[game_key]['name']} بعد. يرجى استخدام أمر `{GAMES_CONFIG[game_key]['setuid_command']}` أولاً.")
        return
    
    uid = users_data[user_id][game_key]
    await event.respond("جارٍ جلب الشخصيات المتوفرة في واجهة العرض...")
    
    characters_data = fetch_enka_api_data(game_key, uid)
    
    if not characters_data:
        await event.respond(f"لا توجد شخصيات متاحة في واجهة العرض لـUID `{uid}`. تأكد من أن حسابك عام وأن لديك شخصيات معروضة.")
        return
    
    # إنشاء الأزرار
    buttons = []
    available_characters = list(characters_data.keys())
    for i in range(0, len(available_characters), 3):
        row = []
        for char_name in available_characters[i:i+3]:
            row.append(Button.inline(char_name, f"character_{game_key}_{char_name}"))
        buttons.append(row)
        
    await bot.send_message(
        event.chat_id,
        f"اختر شخصية من لعبة {GAMES_CONFIG[game_key]['name']} (المتوفرة حالياً):",
        buttons=buttons
    )

# أمر لجلب الشخصية من خلال كتابة اسمها
@bot.on(events.NewMessage(pattern='/(gen|hsr|zzz)'))
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
    
    characters_data = fetch_enka_api_data(game_key, uid)

    if not characters_data or character_name not in characters_data:
        await event.respond(
            f"لم يتم العثور على صورة الشخصية '{character_name}' للعبة {GAMES_CONFIG[game_key]['name']}. "
            f"تأكد من أن اسم الشخصية صحيح وأنها معروضة في واجهة العرض داخل اللعبة."
        )
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
        
        characters_data = fetch_enka_api_data(game_key, uid)
        if not characters_data or character_name not in characters_data:
            await bot.edit_message(event.chat_id, event.message_id,
                f"لم يتم العثور على صورة الشخصية '{character_name}' للعبة {GAMES_CONFIG[game_key]['name']}. "
                f"تأكد من أن اسم الشخصية صحيح وأنها معروضة في واجهة العرض داخل اللعبة."
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
