import os
import json
import telebot
from flask import Flask
from threading import Thread
from datetime import datetime, timezone, timedelta
import time
import utils
from upstash_redis import Redis

TOKEN = os.environ.get('BOT_TOKEN', 'သင့်_Bot_Token_ကို_ဒီနေရာမှာ_ထည့်ပါ')
bot = telebot.TeleBot(TOKEN)

# Upstash Redis Client (Environment Variable ကနေ အလိုအလျောက် ဖတ်ပါမယ်)
redis = Redis.from_env()

app = Flask(__name__)

MAX_EMAILS = 10
EMAIL_LIFETIME = timedelta(days=7)
CLEANUP_INTERVAL = 60 * 60  # ၁ နာရီတစ်ခါ စစ်ဆေးမည်

def utc_now():
    return datetime.now(timezone.utc)

def parse_created_at(value):
    try:
        created_at = datetime.fromisoformat(value)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None

def load_user_data(chat_id):
    """Redis ကနေ User တစ်ယောက်ချင်းစီရဲ့ Email စာရင်းကို ဖတ်ပါ"""
    try:
        data = redis.get(f"user:{chat_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"Redis load error: {e}")
    return []

def save_user_data(chat_id, emails):
    """Redis ထဲကို User ရဲ့ Email စာရင်း သိမ်းပါ"""
    try:
        redis.set(f"user:{chat_id}", json.dumps(emails, ensure_ascii=False))
    except Exception as e:
        print(f"Redis save error: {e}")

def get_all_chat_ids():
    """Redis ထဲမှာ ရှိတဲ့ User အားလုံးရဲ့ chat_id စာရင်းကို ရယူပါ"""
    try:
        keys = redis.keys("user:*")
        return [key.replace("user:", "") for key in keys]
    except Exception as e:
        print(f"Redis keys error: {e}")
        return []

def cleanup_expired_emails():
    """၇ ရက်ကျော်သွားတဲ့ Email တွေကို ဖျက်ပါ"""
    now = utc_now()
    for chat_id in get_all_chat_ids():
        emails = load_user_data(chat_id)
        active_emails = []
        changed = False

        for item in emails:
            created_at = parse_created_at(item.get('created_at'))
            if created_at is None:
                item['created_at'] = now.isoformat()
                created_at = now
                changed = True

            if now - created_at >= EMAIL_LIFETIME:
                try:
                    utils.Delete_Account(item.get('token', ''))
                except Exception as error:
                    print(f"Could not delete expired account: {error}")
                changed = True
                continue
            active_emails.append(item)

        if changed:
            save_user_data(chat_id, active_emails)

def cleanup_loop():
    while True:
        try:
            cleanup_expired_emails()
        except Exception as error:
            print(f"Cleanup error: {error}")
        time.sleep(CLEANUP_INTERVAL)

cleanup_expired_emails()

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ================== Bot Commands ==================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Use /mail for menu.")

@bot.message_handler(commands=['mail'])
def mail_menu(message):
    cleanup_expired_emails()
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("📧 New Email", callback_data="new_email")
    btn2 = telebot.types.InlineKeyboardButton("📋 Email List", callback_data="email_list")
    btn3 = telebot.types.InlineKeyboardButton("📥 Email Inbox", callback_data="inbox")
    btn4 = telebot.types.InlineKeyboardButton("🗑 Delete Email", callback_data="delete_email")
    btn5 = telebot.types.InlineKeyboardButton("❌ Close", callback_data="close")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    bot.send_message(message.chat.id, "Welcome to mail menu.", reply_markup=markup)

# ================== Button Handlers ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    cleanup_expired_emails()
    chat_id = str(call.message.chat.id)

    if call.data == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

    elif call.data == "new_email":
        emails = load_user_data(chat_id)
        if len(emails) >= MAX_EMAILS:
            bot.answer_callback_query(call.id, f"သင့်မှာ Email {MAX_EMAILS} ခုအထိ ရှိပြီးပါပြီ။")
            return
        bot.answer_callback_query(call.id, "Email အသစ် ဖန်တီးနေပါတယ်...")
        success, result = utils.Generate_Email()
        if success:
            email, password, token = result
            emails.append({
                "email": email,
                "password": password,
                "token": token,
                "created_at": utc_now().isoformat()
            })
            save_user_data(chat_id, emails)
            bot.send_message(call.message.chat.id, f"✅ သင့် Email အသစ်:\n{email}\n\nဒီ Email သည် ၇ ရက်အကြာတွင် အလိုအလျောက် ဖျက်ပါမည်။")
        else:
            bot.send_message(call.message.chat.id, f"❌ Error: {result}")

    elif call.data == "email_list":
        emails = load_user_data(chat_id)
        if not emails:
            bot.send_message(call.message.chat.id, "❌ Email မရှိသေးပါ။ New Email ကို အရင်နှိပ်ပါ။")
        else:
            msg = "📧 သင့် Email များ:\n\n"
            for i, item in enumerate(emails):
                msg += f"{i + 1}. {item['email']}\n"
            bot.send_message(call.message.chat.id, msg)

    elif call.data == "inbox":
        emails = load_user_data(chat_id)
        if not emails:
            bot.send_message(call.message.chat.id, "❌ Email မရှိသေးပါ။ New Email ကို အရင်နှိပ်ပါ။")
        elif len(emails) == 1:
            bot.answer_callback_query(call.id, "Inbox စစ်ဆေးနေပါတယ်...")
            fetch_inbox(call.message.chat.id, emails[0]['token'])
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            for i, item in enumerate(emails):
                markup.add(telebot.types.InlineKeyboardButton(f"📧 {item['email']}", callback_data=f"inbox_{i}"))
            bot.send_message(call.message.chat.id, "စစ်ဆေးလိုသော Email ကို ရွေးပါ:", reply_markup=markup)

    elif call.data.startswith("inbox_"):
        try:
            idx = int(call.data.split("_", 1)[1])
        except ValueError:
            bot.answer_callback_query(call.id, "Email မတွေ့ပါ။")
            return
        emails = load_user_data(chat_id)
        if 0 <= idx < len(emails):
            bot.answer_callback_query(call.id, "Inbox စစ်ဆေးနေပါတယ်...")
            fetch_inbox(call.message.chat.id, emails[idx]['token'])
        else:
            bot.answer_callback_query(call.id, "Email မတွေ့ပါ။")

    elif call.data == "delete_email":
        emails = load_user_data(chat_id)
        if not emails:
            bot.send_message(call.message.chat.id, "❌ ဖျက်ရန် Email မရှိပါ။")
        elif len(emails) == 1:
            success, _ = utils.Delete_Account(emails[0]['token'])
            if success:
                emails.pop(0)
                save_user_data(chat_id, emails)
                bot.send_message(call.message.chat.id, "🗑 Email ကို ဖျက်လိုက်ပါပြီ။")
            else:
                bot.send_message(call.message.chat.id, "❌ ဖျက်လို့မရပါ။")
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            for i, item in enumerate(emails):
                markup.add(telebot.types.InlineKeyboardButton(f"🗑 {item['email']}", callback_data=f"delete_{i}"))
            bot.send_message(call.message.chat.id, "ဖျက်လိုသော Email ကို ရွေးပါ:", reply_markup=markup)

    elif call.data.startswith("delete_"):
        try:
            idx = int(call.data.split("_", 1)[1])
        except ValueError:
            bot.answer_callback_query(call.id, "Email မတွေ့ပါ။")
            return
        emails = load_user_data(chat_id)
        if 0 <= idx < len(emails):
            success, _ = utils.Delete_Account(emails[idx]['token'])
            if success:
                emails.pop(idx)
                save_user_data(chat_id, emails)
                bot.send_message(call.message.chat.id, "🗑 Email ကို ဖျက်လိုက်ပါပြီ။")
            else:
                bot.send_message(call.message.chat.id, "❌ ဖျက်လို့မရပါ။")
        else:
            bot.answer_callback_query(call.id, "Email မတွေ့ပါ။")

def fetch_inbox(chat_id, token):
    success, messages = utils.Load_Mail_Box(token)
    if success:
        if not messages:
            bot.send_message(chat_id, "📭 Inbox ထဲမှာ Email မရှိသေးပါဘူး။")
        else:
            for msg in messages:
                bot.send_message(chat_id, msg['text'])
                if msg.get('attachments'):
                    for att in msg['attachments']:
                        bot.send_message(chat_id, f"📎 ဖိုင် တွေ့ရှိပါတယ် — {att['filename']}\nဒေါင်းလုဒ်လုပ်နေပါတယ်...")
                        success_dl, file_data = utils.Download_Attachment(token, msg['id'], att['id'], att['filename'])
                        if success_dl:
                            bot.send_document(chat_id, file_data)
                        else:
                            bot.send_message(chat_id, f"❌ ဖိုင်ဒေါင်းလုဒ် မအောင်မြင်ပါ: {file_data}")
    else:
        bot.send_message(chat_id, f"❌ Error: {messages}")

# ================== Main ==================
if __name__ == "__main__":
    cleanup_thread = Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    print("Bot is starting...")
    bot.infinity_polling()
