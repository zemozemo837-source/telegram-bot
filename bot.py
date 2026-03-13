import telebot
import time
import os
import threading
import requests
from flask import Flask

TOKEN = os.getenv("BOT_TOKEN")
# Укажи свой URL на Render, например: https://my-bot.onrender.com
RENDER_URL = os.getenv("RENDER_URL", "")

bot = telebot.TeleBot(TOKEN, threaded=True)

# Слова которые разрешают сообщение обычным участникам
ALLOWED_WORDS = ["ищу", "сниму", "арендую"]

# Кэш администраторов {chat_id: (timestamp, set_of_admin_ids)}
admin_cache = {}
ADMIN_CACHE_TTL = 300  # 5 минут

# Защита от дублей предупреждений {user_id: timestamp}
recent_warnings = {}
WARNING_COOLDOWN = 15  # секунд

# Защита от медиагрупп (альбомов) {media_group_id: timestamp}
handled_media_groups = {}
MEDIA_GROUP_TTL = 10  # секунд


def get_admin_ids(chat_id):
    """Получает id админов с кэшем на 5 минут."""
    now = time.time()
    cached = admin_cache.get(chat_id)
    if cached and now - cached[0] < ADMIN_CACHE_TTL:
        return cached[1]
    try:
        admins = bot.get_chat_administrators(chat_id)
        ids = {a.user.id for a in admins}
        admin_cache[chat_id] = (now, ids)
        print(f"Admin cache updated: {len(ids)} admins")
        return ids
    except Exception as e:
        print(f"ERROR get_admin_ids: {e}")
        return cached[1] if cached else set()


def cleanup():
    """Чистим старые записи."""
    now = time.time()
    for uid in list(recent_warnings.keys()):
        if now - recent_warnings[uid] > WARNING_COOLDOWN * 5:
            del recent_warnings[uid]
    for gid in list(handled_media_groups.keys()):
        if now - handled_media_groups[gid] > MEDIA_GROUP_TTL * 5:
            del handled_media_groups[gid]


def send_and_delete_warning(chat_id, delay=10):
    """Отправляет предупреждение и удаляет его через delay секунд."""
    try:
        msg = bot.send_message(
            chat_id,
            "❗ Публиковать объявления могут только риелторы.\n\n"
            "Для размещения объявления напишите администратору:\n"
            "@Batumi1123"
        )
        time.sleep(delay)
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        print(f"ERROR send_warning: {e}")


def self_ping():
    """
    Пингует сам себя каждые 5 минут чтобы Render не засыпал.
    Запускается в отдельном потоке.
    """
    if not RENDER_URL:
        print("RENDER_URL не задан — самопинг отключён")
        return
    while True:
        time.sleep(270)  # 4.5 минуты
        try:
            r = requests.get(f"{RENDER_URL}/ping", timeout=10)
            print(f"Self-ping: {r.status_code}")
        except Exception as e:
            print(f"Self-ping error: {e}")


@bot.message_handler(content_types=[
    'text', 'photo', 'video', 'document',
    'audio', 'voice', 'sticker', 'animation'
])
def check_message(message):
    try:
        chat_id = message.chat.id
        msg_id = message.message_id
        user_id = message.from_user.id
        media_group_id = getattr(message, 'media_group_id', None)

        # Собираем текст
        text = ""
        if message.text:
            text = message.text.lower()
        elif message.caption:
            text = message.caption.lower()

        print(f"MSG uid={user_id} mgid={media_group_id} text={text[:50]!r}")

        # Пропускаем администраторов и риелторов
        admin_ids = get_admin_ids(chat_id)
        if user_id in admin_ids:
            print("ADMIN — skip")
            return

        # Пропускаем разрешённые слова
        if any(word in text for word in ALLOWED_WORDS):
            print("ALLOWED — skip")
            return

        # Удаляем сообщение
        try:
            bot.delete_message(chat_id, msg_id)
            print(f"DELETED msg {msg_id}")
        except Exception as e:
            print(f"Delete error: {e}")

        # Защита от дублей
        now = time.time()
        cleanup()

        # Альбом — одно предупреждение на всю группу фото
        if media_group_id:
            if media_group_id in handled_media_groups:
                print(f"Album {media_group_id} already handled — skip")
                return
            handled_media_groups[media_group_id] = now

        # Кулдаун на пользователя
        if now - recent_warnings.get(user_id, 0) < WARNING_COOLDOWN:
            print(f"Cooldown for uid={user_id} — skip")
            return

        recent_warnings[user_id] = now

        # Предупреждение в отдельном потоке (не блокируем основной)
        threading.Thread(
            target=send_and_delete_warning,
            args=(chat_id,),
            daemon=True
        ).start()

    except Exception as e:
        print(f"HANDLER ERROR: {e}")


# ---- Flask для Render ----
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running", 200

@app.route("/ping")
def ping():
    from flask import Response
    return Response("ok", status=200, mimetype="text/plain")


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def run_bot():
    print("Бот запущен, polling...")
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except Exception as e:
            print(f"POLLING ERROR: {e} — перезапуск через 5 сек")
            time.sleep(5)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    run_bot()
