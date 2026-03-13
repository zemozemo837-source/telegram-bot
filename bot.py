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

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

recent_warnings = {}
processed_groups = {}

# ---------------- DELETE WARNING LATER ----------------

def delete_warning_later(chat_id, message_id):
    time.sleep(7)
    try:
        bot.delete_message(chat_id, message_id)
        logging.info("WARNING DELETED")
    except:
        pass


# ---------------- BOT LOGIC ----------------

@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):

    try:

        text = ""

        if message.text:
            text += message.text.lower()

        if message.caption:
            text += message.caption.lower()

        logging.info(f"MESSAGE from {message.from_user.id} | {text}")

        # ---- ADMIN CHECK ----

        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        if message.from_user.id in admin_ids:
            return

        # ---- ALLOWED WORDS ----

        if any(word in text for word in allowed_words):
            return

        # ---- MEDIA GROUP (ALBUM) ----

        if message.media_group_id:

            if message.media_group_id in processed_groups:
                return

            processed_groups[message.media_group_id] = True

        # ---- DELETE MESSAGE ----

        bot.delete_message(message.chat.id, message.message_id)
        logging.info("MESSAGE DELETED")

        # ---- WARNING ----

        user_id = message.from_user.id
        now = time.time()

        if user_id in recent_warnings and now - recent_warnings[user_id] < 5:
            return

        recent_warnings[user_id] = now

        msg = bot.send_message(
            message.chat.id,
            "❗ Публиковать объявления могут только риелторы.\n\nДля размещения объявления\nнапишите администратору:\n@Batumi1123"
        )

        logging.info("WARNING SENT")

        threading.Thread(
            target=delete_warning_later,
            args=(message.chat.id, msg.message_id)
        ).start()

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

    logging.info("BOT STARTED")

    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    bot.infinity_polling(skip_pending=True)

