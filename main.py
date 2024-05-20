import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update
import logging
import time
import datetime
import pytz
import json
import re
import socket

# Загрузка настроек
with open('/etc/secrets/settings.json') as json_file:
    settings = json.load(json_file)

# Подключение к Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('/etc/secrets/credentials.json', scope)
client = gspread.authorize(credentials)

# Открытие таблицы по URL
worksheet = client.open_by_url(settings['spreadsheet_url']).worksheet(settings['worksheet'])
statsheet = client.open_by_url(settings['spreadsheet_url']).worksheet(settings['statsheet'])

#Функция обрезки лишних символов на конце строки
def cutlast(s, tail):
    if s[-len(tail):] == tail:
        s = s[:-len(tail)] 
    return s

#Функция вырезания текста между двух строк
def cutbetween(a, b, text):
    m = re.search(a+'(.+?)'+b, text)
    if m:
        return m.group(1)
    else:
        return false

# Функция получения основных данных о сообщении
def getMsgInfo(update):
    #print(update)
    chat_id = update.message.chat.id
    msg_id = update.message.message_id
    msg_date_utc = update.message.forward_date if update.message.forward_date else update.message.date
    tz = pytz.timezone('Europe/Moscow')
    msg_date = msg_date_utc.astimezone(tz).strftime("%d.%m.%Y")
    return [chat_id, msg_id, msg_date]
        
# Функция для обработки команды /start
def start(update, context):
    update.message.reply_text('Привет! Отправь мне данные в формате: {наименование расхода} {стоимость}руб.')

# Функция отправки статистики
def stat(update, context):
    [chat_id, msg_id, msg_date] = getMsgInfo(update)
    total = statsheet.acell('C2').value
    reply = "Статистика за текущий месяц:"
    byCat = statsheet.get('D5:E')
    
    #выравнивание строк
    maxlen = 0
    for row in byCat:
        if maxlen < len(row[0]):
            maxlen = len(row[0])
    
    for row in byCat:
        reply += "\n" + row[0]
        for i in range(maxlen-len(row[0])):
            reply += '  '
        reply += ' '+row[1]+' руб.'
    reply += "\nИтого: "+total+' руб.'
    update.message.reply_text(reply)

# Функция для сохранения данных в Google таблице
def save_data(update, context):
    [chat_id, msg_id, msg_date] = getMsgInfo(update)
    
    data = update.message.text.split()
    cost = data.pop(-1)
    cost = cutlast(cost, 'руб.')
    cost = cutlast(cost, 'руб')
    cost = cutlast(cost, 'р.')
    cost = cutlast(cost, 'р')

    event = ' '.join(data)
    
    answer = False
    if cost.isnumeric() and event:
        row = [msg_id, msg_date, event, cost]
        print(row)
        appended_row = worksheet.append_row(row, value_input_option='USER_ENTERED')
        answer = update.message.reply_text('Данные успешно сохранены в Google таблице.')
        
    else:
        answer = update.message.reply_text('Неверный формат данных. Попробуйте еще раз.')
    
    if answer:
        time.sleep(5)
        updater.bot.delete_message(answer.chat.id,answer.message_id)

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Создание обработчиков команд и сообщений
updater = Updater(settings['bottoken'])
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('stat', stat))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_data))

# Запуск бота
updater.start_polling()
updater.idle()


# Занимаем порт (для бесплатного тарифа render.com
sock = socket.socket()
sock.bind(('', 10000))
sock.listen(1)
conn, addr = sock.accept()

print('connected:', addr)

while True:
    data = conn.recv(1024)
    if not data:
        break
    conn.send(data.upper())

conn.close()
