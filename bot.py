import telebot
import time
from flask import Flask
import threading
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

# защита от спама сообщений бота
recent_warnings = {}

@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):
    try:
        text = ""

        if message.text:
            text = message.text.lower()

        if message.caption:
            text = message.caption.lower()

        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        # админы могут писать всё
        if message.from_user.id in admin_ids:
            return

        # разрешенные слова
        if any(word in text for word in allowed_words):
            return

        # удаляем сообщение
        bot.delete_message(message.chat.id, message.message_id)

        user_id = message.from_user.id

        # если уже предупреждали недавно — не спамим
        now = time.time()
        if user_id in recent_warnings and now - recent_warnings[user_id] < 5:
            return

        recent_warnings[user_id] = now

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
