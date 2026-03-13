import telebot
import time
from flask import Flask
import threading
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logging.error("BOT_TOKEN not found")
    exit()

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

recent_warnings = {}
processed_media_groups = {}

# ---------------- BOT ----------------

@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):

    try:

        text = ""

        if message.text:
            text += message.text.lower()

        if message.caption:
            text += message.caption.lower()

        logging.info(f"MESSAGE from {message.from_user.id} | {text}")

        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        if message.from_user.id in admin_ids:
            logging.info("ADMIN MESSAGE")
            return

        if any(word in text for word in allowed_words):
            logging.info("ALLOWED MESSAGE")
            return

        # -------- MEDIA GROUP CHECK --------

        if message.media_group_id:

            if message.media_group_id in processed_media_groups:
                logging.info("MEDIA GROUP ALREADY PROCESSED")
                return

            processed_media_groups[message.media_group_id] = True

            logging.info("MEDIA GROUP DETECTED")

            time.sleep(1)

        # -------- DELETE MESSAGE --------

        bot.delete_message(message.chat.id, message.message_id)

        logging.info("MESSAGE DELETED")

        # -------- WARNING --------

        user_id = message.from_user.id
        now = time.time()

        if user_id in recent_warnings and now - recent_warnings[user_id] < 5:
            logging.info("WARNING SKIPPED")
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

        logging.error(e)

# ---------------- WEB SERVER ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ---------------- START ----------------

if __name__ == "__main__":

    logging.info("STARTING BOT")

    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    bot.infinity_polling(skip_pending=True)
