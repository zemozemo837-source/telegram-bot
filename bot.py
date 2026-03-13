import telebot
import time
import os
import threading
from flask import Flask

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=True)

# Слова которые разрешают сообщение (обычные участники)
ALLOWED_WORDS = ["ищу", "сниму", "арендую"]

# Кэш администраторов {chat_id: (timestamp, set_of_admin_ids)}
# Обновляется раз в 5 минут — не дёргаем API на каждое сообщение
admin_cache = {}
ADMIN_CACHE_TTL = 300

# Защита от дублей предупреждений
# {user_id: timestamp} — не шлём повторно в течение 15 сек
recent_warnings = {}
WARNING_COOLDOWN = 15

# Защита от медиагрупп (альбомов)
# {media_group_id: timestamp} — альбом = одно предупреждение
handled_media_groups = {}
MEDIA_GROUP_TTL = 10


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
        print(f"Admin cache updated for chat {chat_id}: {ids}")
        return ids
    except Exception as e:
        print(f"ERROR get_admin_ids: {e}")
        return cached[1] if cached else set()


def cleanup():
    """Удаляем старые записи из словарей чтобы не копилась память."""
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

        # --- Защита от дублей предупреждений ---
        now = time.time()
        cleanup()

        # Если это часть альбома — проверяем не обработан ли уже альбом
        if media_group_id:
            if media_group_id in handled_media_groups:
                print(f"Media group {media_group_id} already handled — skip warning")
                return
            handled_media_groups[media_group_id] = now

        # Проверяем кулдаун для пользователя
        last_warn = recent_warnings.get(user_id, 0)
        if now - last_warn < WARNING_COOLDOWN:
            print(f"Warning cooldown for user {user_id} — skip")
            return

        recent_warnings[user_id] = now

        # Отправляем предупреждение в отдельном потоке
        # чтобы sleep(10) не блокировал обработку других сообщений
        threading.Thread(
            target=send_and_delete_warning,
            args=(chat_id,),
            daemon=True
        ).start()

    except Exception as e:
        print(f"HANDLER ERROR: {e}")


# ---- Flask для Render (keepalive) ----
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running", 200

@app.route("/ping")
def ping():
    return "pong", 200


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
    run_bot()
