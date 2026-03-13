import telebot
import time
from flask import Flask
import threading
import os

TOKEN = "8706659971:AAEQwG2iNYKeLcF-ItT4RHYNoI7LkITaGfs"

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

@bot.message_handler(func=lambda message: True, content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):
    try:
        text = message.text.lower() if message.text else ""

        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        if message.from_user.id in admin_ids:
            return

        if any(word in text for word in allowed_words):
            return

        bot.delete_message(message.chat.id, message.message_id)

        msg = bot.send_message(
            message.chat.id,
            "❗ Публиковать объявления могут только риелторы.\n\nДля размещения объявления\nнапишите администратору:\n@Batumi1123"
        )

        time.sleep(7)
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        print(e)

print("Бот запущен")

# ---- WEB SERVER ДЛЯ RENDER ----
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_web).start()
threading.Thread(target=run_bot).start()

