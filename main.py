import os
import telebot
from flask import Flask
from threading import Thread
import utils

# Render ရဲ့ Environment Variable ကနေ Token ကို ယူပါမယ်
TOKEN = os.environ.get('BOT_TOKEN', 'သင့်_Bot_Token_ကို_ဒီနေရာမှာ_ထည့်ပါ')
bot = telebot.TeleBot(TOKEN)

# Render က Web Service အနေနဲ့ run ဖို့ Flask ကို သုံးပါမယ်
app = Flask(__name__)

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

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == "new_email":
        bot.answer_callback_query(call.id, "Email အသစ် ဖန်တီးနေပါတယ်...")
        # ဒီနေရာမှာ utils.Generate_Email() ကို ခေါ်ပြီး အလုပ်လုပ်နိုင်ပါတယ်
        bot.send_message(call.message.chat.id, "ဒီ feature ကို နောက်မှ ထည့်ပါမယ်။")

# ================== Main ==================
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    print("Bot is starting...")
    bot.infinity_polling()
