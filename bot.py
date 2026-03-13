import telebot
import time

TOKEN = "8706659971:AAEQwG2iNYKeLcF-ItT4RHYNoI7LkITaGfs"

bot = telebot.TeleBot(TOKEN)

allowed_words = ["ищу", "сниму"]

@bot.message_handler(func=lambda message: True, content_types=['text','photo','video','document','audio','voice','sticker'])
def check_message(message):
    try:
        text = message.text.lower() if message.text else ""

        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        # администраторы и риелторы могут писать всё
        if message.from_user.id in admin_ids:
            return

        # обычные пользователи могут писать только "ищу" или "сниму"
        if any(word in text for word in allowed_words):
            return

        # удаляем сообщение
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
bot.infinity_polling()