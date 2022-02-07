import telebot
import sqlite3
from math import radians, sin, cos, asin, sqrt
token = '5101692342:AAEIizVB4TfJaK_uGTVFy_lllNVk4MyFb-M'

# def get_db_ready(db_con):
    
#     listOfTables = db_con.execute(
#         """SELECT name 
#         FROM sqlite_master 
#         WHERE type='table'
#         AND name='LOCATIONS'; """).fetchall()

#     if listOfTables == []:
#         # print('Table not found!')
#         with db_con:
#             db_con.execute("""
#                 CREATE TABLE LOCATIONS (
#                     id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#                     name TEXT NOT NULL,
#                     lat REAL NOT NULL,
#                     lon REAL NOT NULL,
#                     photo BLOB
#                 );
#             """)
#     else:
#         # print('Table found!')
#         pass

class DBHelper:
    def __init__(self, dbname="locat.db"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname, check_same_thread=False)

    def setup(self):
        stmt = """CREATE TABLE IF NOT EXISTS LOCATIONS (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    photo BLOB
                );"""
        self.conn.execute(stmt)
        self.conn.commit()

    def add_item(self, user_id, name, lat, lon, photo):
        stmt = "INSERT INTO LOCATIONS (user_id, name, lat, lon, photo) VALUES (?, ?, ?, ?, ?)"
        args = (user_id, name, lat, lon, photo)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_item(self, user_id):
        stmt = "DELETE FROM LOCATIONS WHERE user_id = (?)"
        args = (user_id, )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def get_items(self, user_id):
        stmt = "SELECT name, lat, lon, photo FROM LOCATIONS WHERE user_id = (?) ORDER BY id DESC"
        args = (user_id, )
        return [x for x in self.conn.execute(stmt, args)]


bot = telebot.TeleBot(token)
db = DBHelper()
db.setup()

class Location:
    def __init__(self, user_id):
        self.user_id = user_id
        self.name = None
        self.lat = None
        self.lon = None
        self.photo = None

@bot.message_handler(commands=['start'])
def start_message(message):
	bot.send_message(message.chat.id, 'Welcome...')

@bot.message_handler(commands=['add'])
def handle_add_location(message):
    chat_id = message.chat.id
    locat = Location(message.from_user.id)
    text = "Write the name"
    bot.send_message(chat_id=message.chat.id,text=text)
    bot.register_next_step_handler(message, add_name, locat)

def add_name(message, locat):
    try:
        locat.name = message.text
        msg = bot.reply_to(message, 'Send location')
        bot.register_next_step_handler(msg, add_location, locat)
    except Exception as e:
        bot.reply_to(message, 'Something wrong. Sorry...')

def add_location(message, locat):
    try:
        location = message.location
        locat.lat = location.latitude
        locat.lon = location.longitude
        msg = bot.reply_to(message, 'Send photo')
        bot.register_next_step_handler(msg, add_photo, locat)
    except Exception as e:
        bot.reply_to(message, 'Something wrong. Sorry...')

def add_photo(message, locat):
    try:
        file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
        if file_info.file_size > 1000000:
            bot.reply_to(message, 'Too big picture. Sorry...')
            return None
        downloaded_file = bot.download_file(file_info.file_path)
        locat.photo = sqlite3.Binary(downloaded_file)
        db.add_item(locat.user_id, locat.name, locat.lat, locat.lon, locat.photo)
        msg = bot.reply_to(message, 'Information saved. Thanks')
    except Exception as e:
        bot.reply_to(message, 'Something wrong. Sorry...')

@bot.message_handler(commands=['list'])
def handle_list(message):
    try:
        result = 0
        items = db.get_items(message.from_user.id)
        if len(items) == 0:
            bot.reply_to(message, "Nothing stored")
            return None
        for item in items:
            if result < 10: show_data(message, item)
            result=+1
    except Exception as e:
        bot.reply_to(message, 'Something wrong. Sorry...')

def show_data(message, item):
    msg = "Name: " + item[0]; 
    bot.reply_to(message, msg)
    bot.send_location(message.from_user.id, item[1], item[2])
    bot.send_photo(message.from_user.id, item[3])
    return None

@bot.message_handler(commands=['reset'])
def handle_reset(message):
    db.delete_item(message.from_user.id)

@bot.message_handler(content_types=['location'])
def search_loc(message):
    try:    
        location = message.location
        lat = location.latitude
        lat_r = radians(lat)
        lon = location.longitude
        EARTH_RADIUS_KM=6372.8
        result = False
        items = db.get_items(message.from_user.id)
        if len(items) == 0:
            bot.reply_to(message, "Nothing stored")
            return None
        for item in items:
            lat_1 = item[1]
            lon_1 = item[2]
            phi_Lat = radians(lat - lat_1)
            phi_Long = radians(lon - lon_1)
            lat_1_r = radians(lat_1)
            a = sin(phi_Lat/2)**2 + \
            cos(lat_r) * cos(lat_1_r) * \
            sin(phi_Long/2)**2
            c = 2 * asin(sqrt(a))
            dist = EARTH_RADIUS_KM * c
            if dist <= 0.5:
                show_data(message, item)
                result = True
        if result == False: bot.reply_to(message, "Nothing found.")
    except Exception as e:
        bot.reply_to(message, 'Something wrong. Sorry...')

# bot.polling()
bot.infinity_polling(True)
