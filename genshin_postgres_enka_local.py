
# genshin_postgres_enka_local.py
# Genshin Telegram Bot - Postgres + enkacard local generation
# Features:
# - PostgreSQL via SQLAlchemy for persistence
# - enka for fetching Hoyolab data (optional HOYOLAB_COOKIE)
# - enkacard library used locally to render cards (requires system deps)
# - /bind, /profile, /abyss, /wish, /wishlog, /characters (paginated 3x4 grid)
# - Flask health endpoint for Koyeb

import os, io, random, threading
from datetime import datetime
from flask import Flask, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import requests

# optional libs
try:
    import enka
except Exception:
    enka = None

try:
    import enkacard as enkacard_lib
except Exception:
    enkacard_lib = None

# SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
HOYOLAB_COOKIE = os.getenv("HOYOLAB_COOKIE")
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required (Postgres)")

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    telegram_id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Pity(Base):
    __tablename__ = 'pity'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False)
    banner = Column(String, nullable=False)
    five_star_pity = Column(Integer, default=0)
    four_star_pity = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint('telegram_id', 'banner', name='_telegram_banner_uc'),)

class Wish(Base):
    __tablename__ = 'wishes'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    banner = Column(String, nullable=False)
    rarity = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    time = Column(DateTime, default=datetime.utcnow)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

ENKA_CLIENT = None
if HOYOLAB_COOKIE and enka is not None:
    try:
        ENKA_CLIENT = enka.Client(cookie=HOYOLAB_COOKIE)
    except Exception as e:
        print("enka init failed:", e)
        ENKA_CLIENT = None

BANNERS = {
    'standard': {'five_star_pity': 90, 'four_star_pity': 10},
    'character_event': {'five_star_pity': 90, 'four_star_pity': 10},
    'weapon_event': {'five_star_pity': 80, 'four_star_pity': 10}
}
BASE_PROBS = {'five_star': 0.006, 'four_star': 0.051, 'three_star': 0.943}

def get_or_create_user(db, telegram_id):
    u = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not u:
        u = User(telegram_id=telegram_id)
        db.add(u); db.commit(); db.refresh(u)
    return u

def get_pity_record(db, telegram_id, banner):
    p = db.query(Pity).filter(Pity.telegram_id == telegram_id, Pity.banner == banner).first()
    if not p:
        p = Pity(telegram_id=telegram_id, banner=banner, five_star_pity=0, four_star_pity=0)
        db.add(p); db.commit(); db.refresh(p)
    return p

def perform_single_wish_db(db, telegram_id, banner):
    p = get_pity_record(db, telegram_id, banner)
    p.five_star_pity += 1
    p.four_star_pity += 1
    threshold5 = BANNERS.get(banner, BANNERS['standard'])['five_star_pity']
    threshold4 = BANNERS.get(banner, BANNERS['standard'])['four_star_pity']
    rarity = 3
    if p.five_star_pity >= threshold5:
        rarity = 5
    elif p.four_star_pity >= threshold4:
        rarity = 4
    else:
        r = random.random()
        if r < BASE_PROBS['five_star']:
            rarity = 5
        elif r < BASE_PROBS['five_star'] + BASE_PROBS['four_star']:
            rarity = 4
        else:
            rarity = 3
    if rarity == 5:
        p.five_star_pity = 0; p.four_star_pity = 0
        name = random.choice(['Diluc','Venti','Kazuha','Raiden Shogun','Ayaka'])
    elif rarity == 4:
        p.four_star_pity = 0
        name = random.choice(['Fischl','Noelle','Xiangling','Bennett'])
    else:
        name = random.choice(['Iron Sting','Cool Steel','Harbinger of Dawn'])
    wish = Wish(telegram_id=telegram_id, banner=banner, rarity=rarity, name=name)
    db.add(wish); db.add(p); db.commit(); db.refresh(wish); db.refresh(p)
    return {'rarity': rarity, 'name': name, 'five_star_pity': p.five_star_pity, 'four_star_pity': p.four_star_pity}

def fetch_profile_by_uid(uid):
    if ENKA_CLIENT is None:
        return None, "enka unavailable or HOYOLAB_COOKIE not set"
    try:
        player = ENKA_CLIENT.get_player(uid)
        return player, None
    except Exception as e:
        return None, str(e)

def fetch_abyss_by_uid(uid):
    if ENKA_CLIENT is None:
        return None, "enka unavailable or HOYOLAB_COOKIE not set"
    try:
        abyss = ENKA_CLIENT.get_spiral_abyss(uid)
        return abyss, None
    except Exception as e:
        return None, str(e)

# enkacard local generation helper (character card or profile)
def generate_character_card_image(uid, avatar=None, character_name=None):
    if enkacard_lib is None:
        return None, "enkacard lib not installed"
    try:
        # enkacard usage may vary; common pattern: Card(...).generate_bytes()
        # We attempt to build a card for the character; enkacard API might need adaptation.
        card = None
        if character_name:
            try:
                card = enkacard_lib.CharacterCard(character_name)  # may differ by version
            except Exception:
                # fallback to generic Card with uid param
                card = enkacard_lib.Card(uid)
        else:
            card = enkacard_lib.Card(uid)
        buf = card.generate_bytes()
        return buf, None
    except Exception as e:
        return None, str(e)

def generate_profile_card_image(uid):
    if enkacard_lib is None:
        return None, "enkacard lib not installed"
    try:
        card = enkacard_lib.Card(uid)
        buf = card.generate_bytes()
        return buf, None
    except Exception as e:
        return None, str(e)

# --- Telegram handlers ---
def start(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        get_or_create_user(db, update.effective_user.id)
    finally:
        db.close()
    text = ("مرحباً! هذا بوت Genshin.\n"
            "أوامر: /bind <UID>, /profile, /abyss, /wish, /wishlog, /characters")
    update.message.reply_text(text)

def bind_cmd(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("استخدم: /bind <UID>")
        return
    uid = args[0]
    db = SessionLocal()
    try:
        user = get_or_create_user(db, update.effective_user.id)
        user.uid = str(uid)
        db.add(user); db.commit()
        update.message.reply_text(f"تم حفظ UID {uid}")
    finally:
        db.close()

def wish_cmd(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton('Standard', callback_data='wish_select:standard'), InlineKeyboardButton('Character', callback_data='wish_select:character_event')],
        [InlineKeyboardButton('Weapon', callback_data='wish_select:weapon_event')]
    ]
    update.message.reply_text("اختر البانر للسحب:", reply_markup=InlineKeyboardMarkup(keyboard))

def wish_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if not query.data.startswith('wish_select:'):
        return
    banner = query.data.split(':',1)[1]
    tid = query.from_user.id
    db = SessionLocal()
    try:
        res = perform_single_wish_db(db, tid, banner)
    finally:
        db.close()
    text = f"سحبت على {banner}: {'⭐'*res['rarity']} {res['name']}\nPity -> 5*: {res['five_star_pity']} | 4*: {res['four_star_pity']}"
    # try to generate character/profile card image
    img, err = generate_profile_card_image(db and None or None)  # placeholder; use uid-based generation later
    if img:
        try:
            query.message.reply_photo(photo=img, caption=text)
            return
        except Exception:
            pass
    query.message.reply_text(text)

def pity_cmd(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        tid = update.effective_user.id
        banner = context.args[0] if context.args else 'standard'
        p = get_pity_record(db, tid, banner)
        update.message.reply_text(f"الـ pity الحالي على {banner}: 5* = {p.five_star_pity} ، 4* = {p.four_star_pity}")
    finally:
        db.close()

def wishlog_cmd(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        tid = update.effective_user.id
        rows = db.query(Wish).filter(Wish.telegram_id == tid).order_by(Wish.time.asc()).limit(200).all()
        if not rows:
            update.message.reply_text("لا توجد سحوبات بعد.")
            return
        lines = [f"{i+1}. {'⭐'*r.rarity} {r.name} ({r.banner}) - {r.time.strftime('%Y-%m-%d %H:%M')}" for i,r in enumerate(rows)]
        update.message.reply_text("\\n".join(lines))
    finally:
        db.close()

# Characters command: pagination with 3 columns x 4 rows = 12 buttons per page
def characters_cmd(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        tid = update.effective_user.id
        user = db.query(User).filter(User.telegram_id == tid).first()
        if not user or not user.uid:
            update.message.reply_text("لا يوجد UID مسجل. استخدم /bind <UID>")
            return
        uid = user.uid
        # fetch characters via enka if available
        if ENKA_CLIENT is None:
            update.message.reply_text("enka غير متوفر أو HOYOLAB_COOKIE لم يُضبط.")
            return
        try:
            player = ENKA_CLIENT.get_player(uid)
            chars = player.characters  # enka's player should have characters list; may vary by version
        except Exception as e:
            update.message.reply_text("خطأ عند جلب الشخصيات: " + str(e))
            return
        # format character list as simple list of dicts (id, name)
        char_list = []
        for c in chars:
            # Some enka versions use different attribute names - use best-effort
            name = getattr(c, 'name', getattr(c, 'character', None) or str(c))
            cid = getattr(c, 'id', getattr(c, 'character_id', None) or name)
            char_list.append({'id': cid, 'name': name})
        if not char_list:
            update.message.reply_text("لم يتم العثور على شخصيات في هذا الحساب.")
            return
        # store char_list in user session (cache) via context.user_data for pagination
        context.user_data['char_list'] = char_list
        context.user_data['char_page'] = 0
        send_char_page(update, context, 0)
    finally:
        db.close()

def send_char_page(update: Update, context: CallbackContext, page_index: int):
    char_list = context.user_data.get('char_list', [])
    per_page = 12
    pages = (len(char_list) + per_page - 1) // per_page
    page_index = max(0, min(page_index, pages-1))
    start = page_index * per_page
    end = start + per_page
    page_items = char_list[start:end]
    # build keyboard with 3 columns
    keyboard = []
    row = []
    for i, itm in enumerate(page_items, start=1):
        row.append(InlineKeyboardButton(itm['name'][:20], callback_data=f"char_sel:{start + i - 1}"))
        if len(row) == 3:
            keyboard.append(row); row = []
    if row:
        keyboard.append(row)
    # prev/next buttons
    nav = []
    if page_index > 0:
        nav.append(InlineKeyboardButton("⏮️ السابق", callback_data=f"char_nav:{page_index-1}"))
    if page_index < pages-1:
        nav.append(InlineKeyboardButton("التالي ⏭️", callback_data=f"char_nav:{page_index+1}"))
    if nav:
        keyboard.append(nav)
    update.message.reply_text(f"شخصياتك - صفحة {page_index+1}/{pages}", reply_markup=InlineKeyboardMarkup(keyboard))

def characters_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    if data.startswith("char_nav:"):
        page = int(data.split(":",1)[1])
        context.user_data['char_page'] = page
        send_char_page(query, context, page)
        return
    if data.startswith("char_sel:"):
        idx = int(data.split(":",1)[1])
        char_list = context.user_data.get('char_list', [])
        if idx < 0 or idx >= len(char_list):
            query.message.reply_text("اختيار غير صالح.")
            return
        char = char_list[idx]
        # generate character card locally
        uid = None
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
            uid = user.uid if user else None
        finally:
            db.close()
        img_buf, err = generate_character_card_image(uid, character_name=char['name'])
        caption = f"{char['name']}\\n(معلومات إضافية قد تظهر هنا)"
        if img_buf:
            try:
                query.message.reply_photo(photo=img_buf, caption=caption)
                return
            except Exception as e:
                query.message.reply_text("فشل في إرسال الصورة: " + str(e))
                return
        query.message.reply_text("فشل في توليد صورة الشخصية: " + (err or 'unknown error'))

def profile_cmd(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        tid = update.effective_user.id
        uid = None
        if context.args:
            uid = context.args[0]
        else:
            user = db.query(User).filter(User.telegram_id == tid).first()
            if user and user.uid:
                uid = user.uid
        if not uid:
            update.message.reply_text('لا يوجد UID مسجل. استخدم /bind <UID> أو اكتب /profile <UID>')
            return
        # try generate profile card locally
        img, err = generate_profile_card_image(uid)
        if img:
            try:
                update.message.reply_photo(photo=img, caption=f'Profile UID {uid}')
                return
            except Exception as e:
                update.message.reply_text('فشل في إرسال الصورة: ' + str(e))
                return
        update.message.reply_text('فشل في توليد صورة البروفايل: ' + (err or 'unknown'))
    finally:
        db.close()

def abyss_cmd(update: Update, context: CallbackContext):
    db = SessionLocal()
    try:
        tid = update.effective_user.id
        uid = None
        if context.args:
            uid = context.args[0]
        else:
            user = db.query(User).filter(User.telegram_id == tid).first()
            if user and user.uid:
                uid = user.uid
        if not uid:
            update.message.reply_text('لا يوجد UID مسجل. استخدم /bind <UID> أو اكتب /abyss <UID>')
            return
        img, err = generate_profile_card_image(uid)  # enkacard may support abyss mode; fallback to profile card
        if img:
            try:
                update.message.reply_photo(photo=img, caption=f'Spiral Abyss UID {uid}')
                return
            except Exception as e:
                update.message.reply_text('فشل في إرسال الصورة: ' + str(e))
                return
        update.message.reply_text('فشل في توليد صورة الـ Abyss: ' + (err or 'unknown'))
    finally:
        db.close()

# Flask health app for Koyeb
app = Flask('health')
@app.route('/')
def health():
    return Response('OK', status=200)

def run_health():
    app.run(host='0.0.0.0', port=PORT)

def main():
    t = threading.Thread(target=run_health, daemon=True)
    t.start()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('bind', bind_cmd))
    dp.add_handler(CommandHandler('wish', wish_cmd))
    dp.add_handler(CallbackQueryHandler(wish_callback, pattern='^wish_select:'))
    dp.add_handler(CommandHandler('pity', pity_cmd))
    dp.add_handler(CommandHandler('wishlog', wishlog_cmd))
    dp.add_handler(CommandHandler('characters', characters_cmd))
    dp.add_handler(CallbackQueryHandler(characters_callback, pattern='^char_'))
    dp.add_handler(CommandHandler('profile', profile_cmd))
    dp.add_handler(CommandHandler('abyss', abyss_cmd))
    print('Bot started...')
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
