import telebot
import os
import logging
import time
from flask import Flask
import threading

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
        logging.info(f"DELETED {message_id}")
    except Exception as e:
        logging.error(f"DELETE FAILED: {e}")

@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):

    text = ""

    if message.text:
        text += message.text.lower()

    if message.caption:
        text += message.caption.lower()

    logging.info(f"MESSAGE {message.message_id} TEXT: {text}")

    admins = bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]

    if message.from_user.id in admin_ids:
        logging.info("ADMIN MESSAGE")
        return

    if any(word in text for word in allowed_words):
        logging.info("ALLOWED MESSAGE")
        return

    safe_delete(message.chat.id, message.message_id)

    msg = bot.send_message(
        message.chat.id,
        "❗ Объявления могут публиковать только риелторы"
    )

    def delete_warn():
        time.sleep(7)
        safe_delete(message.chat.id, msg.message_id)

    threading.Thread(target=delete_warn).start()


# ----- WEB SERVER FOR RENDER -----

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))

if __name__ == "__main__":

    threading.Thread(target=run_web).start()

    bot.infinity_polling(skip_pending=True)

