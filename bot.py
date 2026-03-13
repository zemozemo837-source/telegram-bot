import telebot
import time
from flask import Flask
import threading
import os
import logging

# ---------------- LOGGING ----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------- CONFIG ----------------

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logging.error("BOT_TOKEN not found!")
    exit()

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

recent_warnings = {}

# ---------------- BOT LOGIC ----------------

@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):

    try:

        text = ""

        if message.text:
            text += message.text.lower()

        if message.caption:
            text += message.caption.lower()

        logging.info(f"NEW MESSAGE from {message.from_user.id} | TEXT: {text}")

        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        if message.from_user.id in admin_ids:
            logging.info("ADMIN MESSAGE - SKIP")
            return

        if any(word in text for word in allowed_words):
            logging.info("ALLOWED MESSAGE")
            return

        logging.info("DELETE MESSAGE")

        bot.delete_message(message.chat.id, message.message_id)

        user_id = message.from_user.id
        now = time.time()

        if user_id in recent_warnings and now - recent_warnings[user_id] < 5:
            logging.info("WARNING ALREADY SENT")
            return

        recent_warnings[user_id] = now

        msg = bot.send_message(
            message.chat.id,
            "❗ Публиковать объявления могут только риелторы.\n\nДля размещения объявления\nнапишите администратору:\n@Batumi1123"
        )

        logging.info("WARNING SENT")

        time.sleep(7)

        bot.delete_message(message.chat.id, msg.message_id)

        logging.info("WARNING DELETED")

    except Exception as e:

        logging.error(f"ERROR: {e}")


logging.info("BOT STARTED")

# ---------------- WEB SERVER (FOR RENDER) ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"


def run_web():
    logging.info("START WEB SERVER")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


def run_bot():
    logging.info("START TELEGRAM BOT")
    bot.infinity_polling(skip_pending=True)


threading.Thread(target=run_web).start()
threading.Thread(target=run_bot).start()

