import os
import telebot
from flask import Flask
from threading import Thread
import utils
import json

# Render ရဲ့ Environment Variable ကနေ Token ကို ယူပါမယ်
TOKEN = os.environ.get('BOT_TOKEN', 'သင့်_Bot_Token_ကို_ဒီနေရာမှာ_ထည့်ပါ')
bot = telebot.TeleBot(TOKEN)

# Render က Web Service အနေနဲ့ run ဖို့ Flask ကို သုံးပါမယ်
app = Flask(__name__)

# User တစ်ယောက်ချင်းစီရဲ့ Email အချက်အလက်ကို ခေတ္တမှတ်ထားဖို့ (Render restart ဖြစ်ရင် ပျောက်သွားနိုင်ပါတယ်)
user_data = {}

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
    
    if call.data == "close":
        bot.delete_message(chat_id, call.message.message_id)
        
    elif call.data == "new_email":
        bot.answer_callback_query(call.id, "Email အသစ် ဖန်တီးနေပါတယ်...")
        success, result = utils.Generate_Email()
        if success:
            email, password, token = result
            user_data[chat_id] = {"email": email, "password": password, "token": token}
            bot.send_message(chat_id, f"✅ သင့် Email အသစ်:\n`{email}`\n\nInbox စစ်ရန် /mail ကို ပြန်နှိပ်ပါ။", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ Error: {result}")
            
    elif call.data == "email_list":
        if chat_id in user_data:
            bot.send_message(chat_id, f"📧 သင့် Email: `{user_data[chat_id]['email']}`", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ Email မရှိသေးပါ။ New Email ကို အရင်နှိပ်ပါ။")
            
    elif call.data == "inbox":
        if chat_id in user_data:
            bot.answer_callback_query(call.id, "Inbox စစ်ဆေးနေပါတယ်...")
            token = user_data[chat_id]['token']
            success, messages = utils.Load_Mail_Box(token)
            if success:
                if not messages:
                    bot.send_message(chat_id, "📭 Inbox ထဲမှာ Email မရှိသေးပါဘူး။")
                else:
                    for msg in messages:
                        bot.send_message(chat_id, msg)
            else:
                bot.send_message(chat_id, f"❌ Error: {messages}")
        else:
            bot.send_message(chat_id, "❌ Email မရှိသေးပါ။ New Email ကို အရင်နှိပ်ပါ။")
            
    elif call.data == "delete_email":
        if chat_id in user_data:
            token = user_data[chat_id]['token']
            utils.Delete_Account(token)
            del user_data[chat_id]
            bot.send_message(chat_id, "🗑 Email ကို ဖျက်လိုက်ပါပြီ။")
        else:
            bot.send_message(chat_id, "❌ ဖျက်ရန် Email မရှိပါ။")

# ================== Main ==================
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    print("Bot is starting...")
    bot.infinity_polling()