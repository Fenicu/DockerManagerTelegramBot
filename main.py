from sys import stdout
import re


import cherrypy
import docker as Cocker
from loguru import logger
from telebot import TeleBot, types
from telebot.util import extract_arguments


bot = TeleBot('<TOKEN>')

owner = 123456 # owner telegram id
Target = None

WebhookUrl = "Some Url" # url for hook
ListenUrl = "127.0.0.1" # bot listen url
ListenPort = 8080 # bot listen port

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
            logger.info(f'{message.from_user.id} написал: {message.text}')
            if message.from_user.id == owner:
                bot.process_new_updates([update])
        except:
            logger.exception("ОшибОЧКА")
        finally:
            return ""

@bot.message_handler(regexp='🗃 Контейнеры')
@bot.message_handler(commands=['start'])
def MainMenu(message):
    containers = docker.containers.list(all=True)
    out = "Список контейнеров:\n"
    buttons = ["🗃 Контейнеры"]
    for i in containers: 
        select = ""
        if Target == i.short_id:
            select = "✅"
            buttons = ["🗃 Контейнеры", "📦 Выбранный"]
        out += f"<b>{i.name}</b> <code>{i.short_id}</code>: <b>{i.status}</b> {select}\n" \
                f"<code>{i.attrs['Config']['Image']}</code>\n\n"
    out += "Чтобы выбрать контейнер <code>/select ID</code>"
    bot.send_message(message.chat.id, out, parse_mode="html", reply_markup=keyboard(buttons))

@bot.message_handler(regexp='📦 Выбранный')
def ShowContainer(message):
    try:
        container = docker.containers.get(Target)
    except:
        bot.send_message(message.chat.id, f"{Target} не найден", parse_mode="html")
        return
    out = f"Выбран контейнер:\n"
    out += f"<b>{container.name}</b> <code>{container.short_id}</code>: <b>{container.status}</b>\n" \
                f"<code>{container.attrs['Config']['Image']}</code>"
    buttons = ["✅ Старт", "🛑 Стоп", "🔄 Перезапустить", "🗃 Контейнеры"]
    bot.send_message(message.chat.id, out, parse_mode="html", reply_markup=keyboard(buttons))

@bot.message_handler(commands=['select'])
def select(message):
    global Target
    container = extract_arguments(message.text)
    try:
        container = docker.containers.get(container)
    except:
        bot.send_message(message.chat.id, f"{container} не найден", parse_mode="html")
        return
    Target = container.short_id
    out = f"Выбран контейнер:\n"
    out += f"<b>{container.name}</b> <code>{container.short_id}</code>: <b>{container.status}</b>\n" \
                f"<code>{container.attrs['Config']['Image']}</code>"
    buttons = ["✅ Старт", "🛑 Стоп", "🔄 Перезапустить", "🗃 Контейнеры"]
    bot.send_message(message.chat.id, out, parse_mode="html", reply_markup=keyboard(buttons))

@bot.message_handler(regexp='✅ Старт')
def StartContainer(message):
    container = docker.containers.get(Target)
    bot.send_message(message.chat.id, 'Запуск контейнера, ожидайте')
    container.start()
    bot.send_message(message.chat.id, 'Успех!')

@bot.message_handler(regexp='🛑 Стоп')
def StopContainer(message):
    container = docker.containers.get(Target)
    bot.send_message(message.chat.id, 'Остановка контейнера, ожидайте')
    container.stop()
    bot.send_message(message.chat.id, 'Успех!')

@bot.message_handler(regexp='🔄 Перезапустить')
def RestartContainer(message):
    container = docker.containers.get(Target)
    bot.send_message(message.chat.id, 'Перезапуск контейнера, ожидайте')
    container.restart()
    bot.send_message(message.chat.id, 'Успех!')

def keyboard(text=["🗃 Контейнеры"]):
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    bb = []
    for i in text:
        bb.append(types.KeyboardButton(i))
    markup.add(*bb)
    return markup


if __name__ == '__main__':
    bot.delete_webhook()
    bot.set_webhook(url=WebhookUrl)
    logger.info("starting")
    cherrypy.config.update({
        'log.screen': False,
        'server.socket_host': ListenUrl,
        'server.socket_port': ListenPort,
        'engine.autoreload.on': False
    })
    cherrypy.quickstart(WebhookServer(), '/', {'/': {}})