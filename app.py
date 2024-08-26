import os
import sqlite3
import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from config import config_get
import logging
import requests

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(token=config_get('token'), state_storage=state_storage)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


conn = sqlite3.connect('db', check_same_thread=False)
cursor = conn.cursor()

def create_table(table_name):
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            photo_id TEXT NOT NULL,
            Number TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    conn.commit()

tables = ['Pizza', 'Sandwich', 'Drinks', 'Sweets']
for table in tables:
    create_table(table)

def create_orders_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            order_details TEXT NOT NULL,
            delivery TEXT NOT NULL,
            order_number TEXT NOT NULL
        )
    ''')
    conn.commit()

create_orders_table()

def check_table_exists(table_name):
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

for table in tables:
    if check_table_exists(table):
        logger.info(f"Таблиця {table} успішно створена.")
    else:
        logger.error(f"Помилка при створенні таблиці {table}.")

def add_column_if_not_exists(table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

for table in tables:
    add_column_if_not_exists(table, 'Number', 'TEXT')


class OrderForm:
    waiting_for_order = 'waiting_for_order'

class ProductForm(StatesGroup):
    photo = State()
    name = State()
    price = State()
    number = State()
    table = State()
    content = State()

class PasswordForm(StatesGroup):
    password = State()

class EditPriceForm(StatesGroup):
    table = State()
    number = State()
    new_price = State()

class EditNameForm(StatesGroup):
    table = State()
    number = State()
    new_name = State()

class EditPhotoForm(StatesGroup):
    table = State()
    number = State()
    new_photo = State()

class EditContentForm(StatesGroup):
    table = State()
    number = State()
    new_content = State()

class DeleteProductForm(StatesGroup):
    table = State()
    number = State()

# Pagination states
class PaginationState(StatesGroup):
    table = State()
    page = State()

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, "Привіт, я бот піцерії 'Тепло'!!")
    show_start_button(message.chat.id)


def show_start_button(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_start = types.KeyboardButton('Start')
    markup.add(btn_start)
    bot.send_message(chat_id, "Натисніть 'Start' для початку роботи:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Start')
def handle_start_button(message):
    bot.send_message(message.chat.id,
                     "Тут ти можеш переглянути меню та зробити замовлення, тож натискай кнопки скоріш!)\n")
    show_menu(message.chat.id)

def show_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_catalog_command = types.KeyboardButton('Меню')
    btn_order = types.KeyboardButton('Створити замовлення')
    markup.row(btn_catalog_command,btn_order)
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)


@bot.message_handler(commands=['admin'])
def input_handler(message):
    bot.send_message(message.chat.id, "Для використання цієї функції ведіть пароль")
    bot.set_state(message.from_user.id, PasswordForm.password, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == PasswordForm.password.name,
    content_types=['text'])
def process_password(message):
    password = message.text
    if password == '25082024':
        bot.send_message(message.chat.id, "Пароль вірний!")
        show_fill_menu(message.chat.id)
        bot.delete_state(message.from_user.id, message.chat.id)
    else:
        bot.send_message(message.chat.id, "Пароль не вірний. Спробуйте ще раз.")
        bot.delete_state(message.from_user.id, message.chat.id)


def show_fill_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add_product = types.KeyboardButton('Додати позицію')
    btn_edit_product = types.KeyboardButton('Редагувати позицію')
    delete_order_button = types.KeyboardButton('Видалити Замовлення')
    markup.row(btn_add_product, btn_edit_product,delete_order_button)
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)



@bot.message_handler(func=lambda message: message.text == 'Меню')
def get_catalog_button_handler(message):
    show_catalog_menu(message.chat.id)


def show_catalog_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_pizza = types.KeyboardButton('Піца')
    btn_sandwich = types.KeyboardButton('Сендвічі')
    btn_drinks = types.KeyboardButton('Напої')
    btn_sweets = types.KeyboardButton('Солодощі')
    btn_go_back = types.KeyboardButton('Назад')
    markup.row(btn_pizza, btn_sandwich, btn_drinks, btn_sweets, btn_go_back)
    bot.send_message(chat_id, "Оберіть категорію:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Піца')
@bot.message_handler(func=lambda message: message.text == 'Сендвічі')
@bot.message_handler(func=lambda message: message.text == 'Напої')
@bot.message_handler(func=lambda message: message.text == 'Солодощі')
def handle_product_category(message):
    category = message.text
    category_table_map = {
        'Піца': 'Pizza',
        'Сендвічі': 'Sandwich',
        'Напої': 'Drinks',
        'Солодощі': 'Sweets'
    }
    table_name = category_table_map.get(category, None)
    if table_name:
        bot.send_message(message.chat.id, f"Перегляд категорії: {category}")

        if table_name == 'Pizza':
            get_pizza(message)
        if table_name == 'Sandwich':
            get_sandwich(message)
        if table_name == 'Drinks':
            get_drinks(message)
        if table_name == 'Sweets':
            get_sweets(message)

    else:
        bot.send_message(message.chat.id, "Категорія не знайдена.")


def get_pizza(message):
    cursor.execute("SELECT photo_id, number, title, content, price FROM Pizza")
    products = cursor.fetchall()

    for product in products:
        photo_id, number, title, content, price = product
        bot.send_photo(message.chat.id, photo_id, caption=f'Номер: {number}\n{title}\n{content}\n{price} грн')


def get_sandwich(message):
    cursor.execute("SELECT photo_id, number, title, content, price FROM Sandwich")
    products = cursor.fetchall()

    for product in products:
        photo_id, number, title, content, price = product
        bot.send_photo(message.chat.id, photo_id, caption=f'Номер: {number}\n{title}\n{content}\n{price} грн')


def get_drinks(message):
    cursor.execute("SELECT photo_id, number, title, content, price FROM Drinks")
    products = cursor.fetchall()
    for product in products:
        photo_id, number, title, content, price = product
        bot.send_photo(message.chat.id, photo_id, caption=f'Номер: {number}\n{title}\n{content}\n{price} грн')


def get_sweets(message):
    cursor.execute("SELECT photo_id, number, title, content, price FROM Sweets")
    products = cursor.fetchall()

    for product in products:
        photo_id, number, title, content, price = product
        bot.send_photo(message.chat.id, photo_id, caption=f'Номер: {number}\n{title}\n{content}\n{price} грн')


@bot.message_handler(func=lambda message: message.text == 'Додати позицію')
def add_product_handler(message):
    bot.send_message(message.chat.id,
                     "Зазначте в яку категорію ви хочете додати нову позицію:\n/Pizza\n/Sandwich\n/Drinks\n/Sweets")
    bot.set_state(message.from_user.id, ProductForm.table, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == ProductForm.table.name,
    content_types=['text'])
def process_product_table(message):
    table_name = message.text.strip('/')

    bot.send_message(message.chat.id, "Додайте фото")
    bot.set_state(message.from_user.id, ProductForm.photo, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['table'] = table_name


@bot.message_handler(content_types=['photo'],
                     func=lambda message: bot.get_state(message.from_user.id,
                                                        message.chat.id) == ProductForm.photo.name)
def process_product_photo(message):
    file_id = message.photo[-1].file_id
    bot.send_message(message.chat.id, "Зазначте назву")
    bot.set_state(message.from_user.id, ProductForm.name, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['photo'] = file_id


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == ProductForm.name.name,
    content_types=['text'])
def process_product_name(message):
    bot.send_message(message.chat.id, "Зазначте ціну")
    bot.set_state(message.from_user.id, ProductForm.price, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == ProductForm.price.name,
    content_types=['text'])
def process_product_price(message):
    try:
        price = int(message.text)
        bot.send_message(message.chat.id, "Зазначте номер")
        bot.set_state(message.from_user.id, ProductForm.number, message.chat.id)

        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['price'] = price
    except ValueError:
        bot.send_message(message.chat.id, "Ціна має бути цілим числом в копійках. Спробуйте ще раз.")


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == ProductForm.number.name,
    content_types=['text'])
def process_product_number(message):
    bot.send_message(message.chat.id, "Додайте опис")
    bot.set_state(message.from_user.id, ProductForm.content, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['number'] = message.text


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == ProductForm.content.name,
    content_types=['text'])
def process_product_content(message):
    content = message.text

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        table_name = data['table']
        photo = data['photo']
        name = data['name']
        price = data['price']
        number = data['number']

    cursor.execute(
        f"INSERT INTO {table_name} (photo_id, title, price, Number, content) VALUES (?, ?, ?, ?, ?)",
        (photo, name, price, number, content))
    conn.commit()
    bot.send_message(message.chat.id, "Нову позицію додано успішно.")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Редагувати позицію')
def show_edit_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_edit_price = types.KeyboardButton('Редагувати ціну')
    btn_edit_name = types.KeyboardButton('Редагувати назву')
    btn_edit_photo = types.KeyboardButton('Редагувати фото')
    btn_edit_content = types.KeyboardButton('Редагувати опис')
    btn_delete_product = types.KeyboardButton('Видалити позицію')
    markup.row(btn_edit_price, btn_edit_name)
    markup.row(btn_edit_photo, btn_edit_content)
    markup.row(btn_delete_product)
    bot.send_message(message.chat.id, "Оберіть дію:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Редагувати ціну')
def edit_price_handler(message):
    bot.send_message(message.chat.id, "Вкажіть категорію: /Pizza, /Sandwich, /Drinks, /Sweets")
    bot.set_state(message.from_user.id, EditPriceForm.table, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditPriceForm.table.name,
    content_types=['text'])
def process_edit_price_table(message):
    table_name = message.text.strip('/')
    bot.send_message(message.chat.id, "Вкажіть номер позиції")
    bot.set_state(message.from_user.id, EditPriceForm.number, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['table'] = table_name


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditPriceForm.number.name,
    content_types=['text'])
def process_edit_price_number(message):
    number = message.text
    bot.send_message(message.chat.id, "Вкажіть нову ціну")
    bot.set_state(message.from_user.id, EditPriceForm.new_price, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['number'] = number


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditPriceForm.new_price.name,
    content_types=['text'])
def process_new_price(message):
    try:
        new_price = int(message.text)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            table_name = data['table']
            number = data['number']

        cursor.execute(f"UPDATE {table_name} SET price = ? WHERE Number = ?", (new_price, number))
        conn.commit()

        bot.send_message(message.chat.id, "Ціна успішно змінена.")
        bot.delete_state(message.from_user.id, message.chat.id)
    except ValueError:
        bot.send_message(message.chat.id, "Ціна має бути цілим числом в копійках. Спробуйте ще раз.")


@bot.message_handler(func=lambda message: message.text == 'Редагувати назву')
def edit_name_handler(message):
    bot.send_message(message.chat.id, "Вкажіть категорію: /Pizza, /Sandwich, /Drinks, /Sweets")
    bot.set_state(message.from_user.id, EditNameForm.table, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditNameForm.table.name,
    content_types=['text'])
def process_edit_name_table(message):
    table_name = message.text.strip('/')
    bot.send_message(message.chat.id, "Вкажіть номер позиції")
    bot.set_state(message.from_user.id, EditNameForm.number, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['table'] = table_name


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditNameForm.number.name,
    content_types=['text'])
def process_edit_name_number(message):
    number = message.text
    bot.send_message(message.chat.id, "Вкажіть нову назву")
    bot.set_state(message.from_user.id, EditNameForm.new_name, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['number'] = number


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditNameForm.new_name.name,
    content_types=['text'])
def process_new_name(message):
    new_name = message.text

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        table_name = data['table']
        number = data['number']

    cursor.execute(f"UPDATE {table_name} SET title = ? WHERE Number = ?", (new_name, number))
    conn.commit()

    bot.send_message(message.chat.id, "Назву успішно змінено.")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Редагувати фото')
def edit_photo_handler(message):
    bot.send_message(message.chat.id, "Вкажіть категорію: /Pizza, /Sandwich, /Drinks, /Sweets")
    bot.set_state(message.from_user.id, EditPhotoForm.table, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditPhotoForm.table.name,
    content_types=['text'])
def process_edit_photo_table(message):
    table_name = message.text.strip('/')
    bot.send_message(message.chat.id, "Вкажіть номер позиції")
    bot.set_state(message.from_user.id, EditPhotoForm.number, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['table'] = table_name


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditPhotoForm.number.name,
    content_types=['text'])
def process_edit_photo_number(message):
    number = message.text
    bot.send_message(message.chat.id, "Додайте нове фото")
    bot.set_state(message.from_user.id, EditPhotoForm.new_photo, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['number'] = number


@bot.message_handler(content_types=['photo'],
                     func=lambda message: bot.get_state(message.from_user.id,
                                                        message.chat.id) == EditPhotoForm.new_photo.name)
def process_new_photo(message):
    file_id = message.photo[-1].file_id

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        table_name = data['table']
        number = data['number']

    cursor.execute(f"UPDATE {table_name} SET photo_id = ? WHERE Number = ?", (file_id, number))
    conn.commit()

    bot.send_message(message.chat.id, "Фото успішно змінено.")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Редагувати опис')
def edit_content_handler(message):
    bot.send_message(message.chat.id, "Вкажіть категорію: /Pizza, /Sandwich, /Drinks, /Sweets")
    bot.set_state(message.from_user.id, EditContentForm.table, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditContentForm.table.name,
    content_types=['text'])
def process_edit_content_table(message):
    table_name = message.text.strip('/')
    bot.send_message(message.chat.id, "Вкажіть номер позиції")
    bot.set_state(message.from_user.id, EditContentForm.number, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['table'] = table_name


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditContentForm.number.name,
    content_types=['text'])
def process_edit_content_number(message):
    number = message.text
    bot.send_message(message.chat.id, "Вкажіть новий опис")
    bot.set_state(message.from_user.id, EditContentForm.new_content, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['number'] = number


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == EditContentForm.new_content.name,
    content_types=['text'])
def process_new_content(message):
    new_content = message.text

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        table_name = data['table']
        number = data['number']

    cursor.execute(f"UPDATE {table_name} SET content = ? WHERE Number = ?", (new_content, number))
    conn.commit()
    bot.send_message(message.chat.id, "Опис успішно змінено.")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Видалити позицію')
def delete_product_handler(message):
    bot.send_message(message.chat.id, "Вкажіть категорію: /Pizza, /Sandwich, /Drinks, /Sweets")
    bot.set_state(message.from_user.id, DeleteProductForm.table, message.chat.id)


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == DeleteProductForm.table.name,
    content_types=['text'])
def process_delete_product_table(message):
    table_name = message.text.strip('/')
    bot.send_message(message.chat.id, "Вкажіть номер позиції")
    bot.set_state(message.from_user.id, DeleteProductForm.number, message.chat.id)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['table'] = table_name


@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == DeleteProductForm.number.name,
    content_types=['text'])
def process_delete_product_number(message):
    number = message.text

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        table_name = data['table']

    cursor.execute(f"DELETE FROM {table_name} WHERE Number = ?", (number,))
    conn.commit()

    bot.send_message(message.chat.id, "Позицію видалено успішно.")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Категорії')
def show_category_buttons(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_pizza = types.KeyboardButton('Піца')
    btn_sandwich = types.KeyboardButton('Сендвіч')
    btn_drinks = types.KeyboardButton('Напої')
    btn_sweets = types.KeyboardButton('Десерти')
    markup.row(btn_pizza, btn_sandwich)
    markup.row(btn_drinks, btn_sweets)
    bot.send_message(message.chat.id, "Оберіть категорію:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in ['Піца', 'Сендвіч', 'Напої', 'Десерти'])
def show_category_items(message):
    table_name = ''
    if message.text == 'Піца':
        table_name = 'Pizza'
    elif message.text == 'Сендвіч':
        table_name = 'Sandwich'
    elif message.text == 'Напої':
        table_name = 'Drinks'
    elif message.text == 'Десерти':
        table_name = 'Sweets'

    cursor.execute(f"SELECT Number, title, price FROM {table_name}")
    items = cursor.fetchall()

    response = f"{message.text}:\n"
    for item in items:
        number, title, price = item
        response += f"{number}. {title} - {price}грн\n"

    bot.send_message(message.chat.id, response)


@bot.message_handler(func=lambda message: message.text == 'Створити замовлення')
def handle_create_order(message):
    logger.debug(f"Користувач {message.from_user.id} натиснув кнопку 'Створити замовлення'")
    bot.send_message(
        message.chat.id,
        ("Я уважно вас слухаю!\n"
         "Ось приклад замовлення:\n"
         "Я хочу Піцу карбонара, Маямі та М'ясну\n"
         "Доставка/Самовивіз\n"
         "Та вкажіть час доставки чи самовивозу\n"
         "Якщо виникнуть питання дзвоніть за номером:\n"
         "073 505 15 51")
    )
    bot.set_state(message.from_user.id, OrderForm.waiting_for_order, message.chat.id)
    logger.debug(f"Стан бота встановлений на очікування замовлення для користувача {message.from_user.id}")

@bot.message_handler(
    func=lambda message: bot.get_state(message.from_user.id, message.chat.id) == OrderForm.waiting_for_order)
def process_order(message):
    order_details = message.text
    logger.debug(f"Отримано замовлення від користувача {message.from_user.id}: {order_details}")
    bot.send_message(message.chat.id, "Ваше замовлення прийняте!")

    # Використання chat_id групи
    group_chat_id = '-4550209649'  # Замініть на фактичний chat_id вашої групи
    logger.debug(f"Відправка замовлення адміністратору в чат {group_chat_id}")

    try:
        # Відправка замовлення адміністратору
        response = bot.send_message(group_chat_id, f"Отримано нове замовлення:\n{order_details}")
        logger.debug(f"API Response: {response}")
    except Exception as e:
        logger.error(f"Помилка відправки повідомлення адміністратору: {e}")

    # Видалення стану після обробки замовлення
    bot.delete_state(message.from_user.id, message.chat.id)
    logger.debug(f"Стан бота видалений для користувача {message.from_user.id}")

@bot.message_handler(commands=['get_chat_id'])
def send_chat_id(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, f"Chat ID: {chat_id}")

if __name__ == "__main__":
    try:
        logger.info("Бот запущений та готовий до роботи.")
        bot.polling(none_stop=True, interval=0, timeout=20, skip_pending=True)
    except Exception as e:
        logger.error(f"Помилка під час роботи бота: {e}")