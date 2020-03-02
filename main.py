from sys import stdout
import re


import cherrypy
import docker as Cocker
from loguru import logger
from telebot import TeleBot, types
from telebot.util import extract_arguments
from pymongo import MongoClient # ===


bot = TeleBot('<TOKEN>')

client = MongoClient() # ===
db = client.docker # ===
db_users = db.Users # ===

logger.remove()
logger.add(stdout, colorize=True, format="<green>{time:YYYY-MM-DD в HH:mm:ss}</green> | <yellow>{level}</yellow> | <cyan>{message}</cyan>")

docker = Cocker.from_env()


class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        try:
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = types.Update.de_json(json_string)
            message = update.message
            user = self.user(message.from_user, message.date) # ===
            logger.info(f'{user["_id"]} написал: {message.text}')
            if user['admin']: # ===
                bot.process_new_updates([update])
        except:
            logger.exception("ОшибОЧКА")
        finally:
            return ""
        
        
    def user(self, user, date): # ===
        if not db_users.find_one({'_id': user.id}): # ===
            base_json = {
                "_id": user.id,
                "register": date,
                "admin": False,
                "target": None}
            logger.info(f"Новый пользователь! | {user.id}")
            db_users.insert_one(base_json) # ===
            return base_json
        user = db_users.find_one({'_id': user.id}) # ===
        return user

@bot.message_handler(regexp='🗃 Контейнеры')
@bot.message_handler(commands=['start'])
def MainMenu(message):
    containers = docker.containers.list(all=True)
    user = db_users.find_one({'_id': message.from_user.id}) # ===
    out = "Список контейнеров:\n"
    buttons = ["🗃 Контейнеры", "🦄 Пользователи"]
    for i in containers: 
        select = ""
        if user["target"] == i.short_id: # =
            select = "✅"
            buttons = ["🗃 Контейнеры", "📦 Выбранный", "🦄 Пользователи"]
        out += f"<b>{i.name}</b> <code>{i.short_id}</code>: <b>{i.status}</b> {select}\n" \
                f"<code>{i.attrs['Config']['Image']}</code>\n\n"
    out += "Чтобы выбрать контейнер <code>/select ID</code>"
    bot.send_message(message.chat.id, out, parse_mode="html", reply_markup=keyboard(buttons))

@bot.message_handler(regexp='📦 Выбранный')
def ShowContainer(message):
    user = db_users.find_one({'_id': message.from_user.id}) # ===
    try:
        container = docker.containers.get(user["target"]) # =
    except:
        bot.send_message(message.chat.id, f"{user['target']} не найден", parse_mode="html")
        return
    out = f"Выбран контейнер:\n"
    out += f"<b>{container.name}</b> <code>{container.short_id}</code>: <b>{container.status}</b>\n" \
                f"<code>{container.attrs['Config']['Image']}</code>"
    buttons = ["✅ Старт", "🛑 Стоп", "🔄 Перезапустить", "🗃 Контейнеры"]
    bot.send_message(message.chat.id, out, parse_mode="html", reply_markup=keyboard(buttons))

@bot.message_handler(commands=['select'])
def select(message):
    container = extract_arguments(message.text)
    try:
        container = docker.containers.get(container)
    except:
        bot.send_message(message.chat.id, f"{container} не найден", parse_mode="html")
        return
    user = db_users.find_one({'_id': message.from_user.id}) # ===
    user["target"] = container.short_id # ==
    db_users.replace_one({'_id': message.from_user.id}, user, True) # ===
    out = f"Выбран контейнер:\n"
    out += f"<b>{container.name}</b> <code>{container.short_id}</code>: <b>{container.status}</b>\n" \
                f"<code>{container.attrs['Config']['Image']}</code>"
    buttons = ["✅ Старт", "🛑 Стоп", "🔄 Перезапустить", "🗃 Контейнеры"]
    bot.send_message(message.chat.id, out, parse_mode="html", reply_markup=keyboard(buttons))

@bot.message_handler(regexp='✅ Старт')
def StartContainer(message):
    user = db_users.find_one({'_id': message.from_user.id}) # ===
    container = docker.containers.get(user["target"]) # =
    bot.send_message(message.chat.id, 'Запуск контейнера, ожидайте')
    container.start()
    bot.send_message(message.chat.id, 'Успех!')

@bot.message_handler(regexp='🛑 Стоп')
def StopContainer(message):
    user = db_users.find_one({'_id': message.from_user.id}) # ===
    container = docker.containers.get(user["target"]) # =
    bot.send_message(message.chat.id, 'Остановка контейнера, ожидайте')
    container.stop()
    bot.send_message(message.chat.id, 'Успех!')

@bot.message_handler(regexp='🔄 Перезапустить')
def RestartContainer(message):
    user = db_users.find_one({'_id': message.from_user.id}) # ===
    container = docker.containers.get(user["target"]) # =
    bot.send_message(message.chat.id, 'Перезапуск контейнера, ожидайте')
    container.restart()
    bot.send_message(message.chat.id, 'Успех!')

@bot.message_handler(regexp='🦄 Пользователи') # ============
def ListUsers(message):
    if not message.from_user.id == 267519921:
        bot.send_message(message.chat.id, "Доступ запрещён", parse_mode="HTML")
        return
    users = db_users.find()
    out = "Список пользователей:\n"
    for user in users:
        out += f"<code>/promote {user['_id']}</code>\n"
    bot.send_message(message.chat.id, out, parse_mode="HTML")


@bot.message_handler(commands=['promote']) # ============
def select(message):
    if not message.from_user.id == 267519921:
        bot.send_message(message.chat.id, "Доступ запрещён", parse_mode="HTML")
        return
    user_id = int(extract_arguments(message.text))
    user = db_users.find_one({'_id': user_id})
    user["admin"] = True
    db_users.replace_one({'_id': user_id}, user, True)
    bot.send_message(message.chat.id, "Успех!", parse_mode="HTML")
    bot.send_message(user_id, "Успех!\nЖмакай /start", parse_mode="HTML")

def keyboard(text=["🗃 Контейнеры", "🦄 Пользователи"]):
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    bb = []
    for i in text:
        bb.append(types.KeyboardButton(i))
    markup.add(*bb)
    return markup


if __name__ == '__main__':
    bot.delete_webhook()
    bot.set_webhook(url="https://telega.fenicu.men/dockermanager")
    logger.info("starting")
    cherrypy.config.update({
        'log.screen': False,
        'server.socket_host': '127.0.0.1',
        'server.socket_port': 5568,
        'engine.autoreload.on': True
    })
    cherrypy.quickstart(WebhookServer(), '/', {'/': {}})