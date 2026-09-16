import os
import telebot
from flask import Flask
from threading import Thread
import utils

# Render ရဲ့ Environment Variable ကနေ Token ကို ယူပါမယ်
TOKEN = os.environ.get('BOT_TOKEN', 'သင့်_Bot_Token_ကို_ဒီနေရာမှာ_ထည့်ပါ')
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# User တစ်ယောက်ချင်းစီအတွက် Email အများကြီး သိမ်းထားဖို့
user_data = {}
MAX_EMAILS = 5

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
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = []

    if call.data == "close":
        bot.delete_message(chat_id, call.message.message_id)

    elif call.data == "new_email":
        if len(user_data[chat_id]) >= MAX_EMAILS:
            bot.answer_callback_query(call.id, f"သင့်မှာ Email {MAX_EMAILS} ခုအထိ ရှိပြီးပါပြီ။")
            return
        bot.answer_callback_query(call.id, "Email အသစ် ဖန်တီးနေပါတယ်...")
        success, result = utils.Generate_Email()
        if success:
            email, password, token = result
            user_data[chat_id].append({"email": email, "password": password, "token": token})
            bot.send_message(chat_id, f"✅ သင့် Email အသစ်:\n`{email}`\n\nInbox စစ်ရန် /mail ကို ပြန်နှိပ်ပါ။", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ Error: {result}")

    elif call.data == "email_list":
        if not user_data[chat_id]:
            bot.send_message(chat_id, "❌ Email မရှိသေးပါ။ New Email ကို အရင်နှိပ်ပါ။")
        else:
            msg = "📧 သင့် Email များ:\n\n"
            for i, item in enumerate(user_data[chat_id]):
                msg += f"{i+1}. `{item['email']}`\n"
            bot.send_message(chat_id, msg, parse_mode="Markdown")

    elif call.data == "inbox":
        emails = user_data[chat_id]
        if not emails:
            bot.send_message(chat_id, "❌ Email မရှိသေးပါ။ New Email ကို အရင်နှိပ်ပါ။")
        elif len(emails) == 1:
            bot.answer_callback_query(call.id, "Inbox စစ်ဆေးနေပါတယ်...")
            fetch_inbox(chat_id, emails[0]['token'])
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            for i, item in enumerate(emails):
                markup.add(telebot.types.InlineKeyboardButton(f"📧 {item['email']}", callback_data=f"inbox_{i}"))
            bot.send_message(chat_id, "စစ်ဆေးလိုသော Email ကို ရွေးပါ:", reply_markup=markup)

    elif call.data.startswith("inbox_"):
        idx = int(call.data.split("_")[1])
        emails = user_data[chat_id]
        if 0 <= idx < len(emails):
            bot.answer_callback_query(call.id, "Inbox စစ်ဆေးနေပါတယ်...")
            fetch_inbox(chat_id, emails[idx]['token'])
        else:
            bot.answer_callback_query(call.id, "Email မတွေ့ပါ။")

    elif call.data == "delete_email":
        emails = user_data[chat_id]
        if not emails:
            bot.send_message(chat_id, "❌ ဖျက်ရန် Email မရှိပါ။")
        elif len(emails) == 1:
            success, _ = utils.Delete_Account(emails[0]['token'])
            if success:
                user_data[chat_id].pop(0)
                bot.send_message(chat_id, "🗑 Email ကို ဖျက်လိုက်ပါပြီ။")
            else:
                bot.send_message(chat_id, "❌ ဖျက်လို့မရပါ။")
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            for i, item in enumerate(emails):
                markup.add(telebot.types.InlineKeyboardButton(f"🗑 {item['email']}", callback_data=f"delete_{i}"))
            bot.send_message(chat_id, "ဖျက်လိုသော Email ကို ရွေးပါ:", reply_markup=markup)

    elif call.data.startswith("delete_"):
        idx = int(call.data.split("_")[1])
        emails = user_data[chat_id]
        if 0 <= idx < len(emails):
            success, _ = utils.Delete_Account(emails[idx]['token'])
            if success:
                user_data[chat_id].pop(idx)
                bot.send_message(chat_id, "🗑 Email ကို ဖျက်လိုက်ပါပြီ။")
            else:
                bot.send_message(chat_id, "❌ ဖျက်လို့မရပါ။")
        else:
            bot.answer_callback_query(call.id, "Email မတွေ့ပါ။")

def fetch_inbox(chat_id, token):
    success, messages = utils.Load_Mail_Box(token)
    if success:
        if not messages:
            bot.send_message(chat_id, "📭 Inbox ထဲမှာ Email မရှိသေးပါဘူး။")
        else:
            for msg in messages:
                bot.send_message(chat_id, msg)
    else:
        bot.send_message(chat_id, f"❌ Error: {messages}")

# ================== Main ==================
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    print("Bot is starting...")
    bot.infinity_polling()