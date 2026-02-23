import telebot
import sqlite3
import random
from telebot import types

# Замените на свой токен (в данном задании он предоставлен)
TOKEN = '8175699315:AAH3jqml9GYgdB3HCHN7HPd97ZUD7jxDW7o'
bot = telebot.TeleBot(TOKEN)

# Подключение к БД
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц (если их нет)
def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 10000,
            car_id INTEGER DEFAULT NULL,
            job TEXT DEFAULT NULL,
            married_to INTEGER DEFAULT NULL,
            business_id INTEGER DEFAULT NULL,
            FOREIGN KEY (car_id) REFERENCES cars(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT,
            model TEXT,
            price INTEGER,
            fuel_consumption REAL,
            tuning_level INTEGER DEFAULT 0,
            fuel REAL DEFAULT 50
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            cost INTEGER,
            income_per_hour INTEGER,
            owner_id INTEGER
        )
    ''')
    conn.commit()

init_db()

# Добавим несколько автомобилей при первом запуске (если таблица пуста)
def populate_cars():
    cursor.execute("SELECT COUNT(*) FROM cars")
    if cursor.fetchone()[0] == 0:
        cars_data = [
            ('BMW', 'M5 F90', 9500000, 12.5),
            ('BMW', 'M8 G90', 12500000, 14.0),
            ('Mercedes', 'E-Class', 5500000, 9.0),
            ('Mercedes', 'S-Class', 11000000, 11.0),
            ('Lada', 'Vesta', 1200000, 7.5),
            ('Lada', 'Granta', 800000, 6.8)
        ]
        for car in cars_data:
            cursor.execute('INSERT INTO cars (brand, model, price, fuel_consumption) VALUES (?,?,?,?)', car)
        conn.commit()

populate_cars()

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('👤 Профиль', '💼 Работа', '🚖 Такси')
    markup.add('🚗 Машина', '🏢 Бизнес', '💍 Брак')
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    bot.send_message(message.chat.id, f"Добро пожаловать в симулятор реальной жизни!\n"
                                      f"У вас 10 000 ₽ на счету. Зарабатывайте, покупайте машины и бизнесы!",
                     reply_markup=main_menu())

# Профиль
@bot.message_handler(func=lambda m: m.text == '👤 Профиль')
def profile(message):
    user_id = message.from_user.id
    user = cursor.execute('SELECT balance, car_id, job, married_to FROM users WHERE user_id=?', (user_id,)).fetchone()
    balance, car_id, job, married = user
    car_info = "Нет машины"
    if car_id:
        car = cursor.execute('SELECT brand, model FROM cars WHERE id=?', (car_id,)).fetchone()
        car_info = f"{car[0]} {car[1]}"
    spouse = "Нет супруга"
    if married:
        spouse_name = cursor.execute('SELECT first_name FROM users WHERE user_id=?', (married,)).fetchone()
        spouse = f"ID {married}"  # в реальности лучше хранить username
    text = f"💰 Баланс: {balance} ₽\n🚗 Машина: {car_info}\n💼 Работа: {job or 'Безработный'}\n💍 Семья: {spouse}"
    bot.send_message(message.chat.id, text)

# Работа
@bot.message_handler(func=lambda m: m.text == '💼 Работа')
def work_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚚 Курьер", callback_data='work_courier'))
    markup.add(types.InlineKeyboardButton("💻 Программист", callback_data='work_programmer'))
    markup.add(types.InlineKeyboardButton("👨‍🔧 Механик", callback_data='work_mechanic'))
    bot.send_message(message.chat.id, "Выберите работу:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('work_'))
def set_work(call):
    job = call.data.split('_')[1]
    cursor.execute('UPDATE users SET job=? WHERE user_id=?', (job, call.from_user.id))
    conn.commit()
    bot.answer_callback_query(call.id, f"Вы устроились {job}!")
    bot.edit_message_text(f"Теперь вы работаете {job}. Используйте эту же команду, чтобы получить зарплату раз в час.",
                          call.message.chat.id, call.message.message_id)

# Такси
@bot.message_handler(func=lambda m: m.text == '🚖 Такси')
def taxi(message):
    user_id = message.from_user.id
    user = cursor.execute('SELECT car_id, balance FROM users WHERE user_id=?', (user_id,)).fetchone()
    if not user[0]:
        bot.send_message(message.chat.id, "У вас нет машины! Сначала купите её.")
        return
    car = cursor.execute('SELECT fuel, fuel_consumption, tuning_level FROM cars WHERE id=?', (user[0],)).fetchone()
    fuel, consumption, tuning = car
    if fuel <= consumption * 0.1:  # минимум 10% от бака для поездки
        bot.send_message(message.chat.id, "⚠️ Мало топлива! Заправьтесь.")
        return
    # Доход за поездку: базовая ставка 500 + бонус за тюнинг
    income = 500 + tuning * 100
    cursor.execute('UPDATE cars SET fuel = fuel - ? WHERE id=?', (consumption, user[0]))
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id=?', (income, user_id))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ Поездка выполнена! Заработано {income} ₽.")

# Покупка машины
@bot.message_handler(func=lambda m: m.text == '🚗 Машина')
def car_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Купить машину", callback_data='buy_car'))
    markup.add(types.InlineKeyboardButton("Моя машина", callback_data='my_car'))
    markup.add(types.InlineKeyboardButton("Заправить", callback_data='fuel_car'))
    markup.add(types.InlineKeyboardButton("Тюнинг", callback_data='tune_car'))
    bot.send_message(message.chat.id, "Управление автомобилем:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_car')
def show_cars(call):
    cars = cursor.execute('SELECT id, brand, model, price FROM cars').fetchall()
    text = "Доступные автомобили:\n"
    for car in cars:
        text += f"{car[0]}. {car[1]} {car[2]} — {car[3]} ₽\n"
    bot.send_message(call.message.chat.id, text + "\nВведите ID машины, которую хотите купить:")

    # Устанавливаем следующий шаг для обработки ввода номера машины
    bot.register_next_step_handler(call.message, process_buy_car)

def process_buy_car(message):
    try:
        car_id = int(message.text)
        user_id = message.from_user.id
        car = cursor.execute('SELECT price FROM cars WHERE id=?', (car_id,)).fetchone()
        if not car:
            bot.send_message(message.chat.id, "Машина с таким ID не найдена.")
            return
        price = car[0]
        balance = cursor.execute('SELECT balance FROM users WHERE user_id=?', (user_id,)).fetchone()[0]
        if balance < price:
            bot.send_message(message.chat.id, "Недостаточно средств!")
            return
        # Проверим, нет ли уже машины
        if cursor.execute('SELECT car_id FROM users WHERE user_id=?', (user_id,)).fetchone()[0]:
            bot.send_message(message.chat.id, "У вас уже есть машина. Продажа пока не реализована.")
            return
        cursor.execute('UPDATE users SET balance = balance - ?, car_id = ? WHERE user_id=?', (price, car_id, user_id))
        conn.commit()
        bot.send_message(message.chat.id, f"Поздравляем! Вы купили машину за {price} ₽.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")

# Заправка
@bot.callback_query_handler(func=lambda call: call.data == 'fuel_car')
def fuel_car(call):
    user_id = call.from_user.id
    car_id = cursor.execute('SELECT car_id FROM users WHERE user_id=?', (user_id,)).fetchone()[0]
    if not car_id:
        bot.answer_callback_query(call.id, "У вас нет машины!")
        return
    car = cursor.execute('SELECT fuel FROM cars WHERE id=?', (car_id,)).fetchone()
    current_fuel = car[0]
    # Цена топлива: например, 55 ₽ за литр
    price_per_liter = 55
    max_fuel = 80  # допустим, бак 80 л
    needed = max_fuel - current_fuel
    if needed <= 0:
        bot.send_message(call.message.chat.id, "Бак уже полный.")
        return
    cost = needed * price_per_liter
    balance = cursor.execute('SELECT balance FROM users WHERE user_id=?', (user_id,)).fetchone()[0]
    if balance < cost:
        bot.send_message(call.message.chat.id, "Недостаточно денег для полной заправки. Сколько литров заправить?")
        bot.register_next_step_handler(call.message, partial_fuel, car_id, price_per_liter)
    else:
        cursor.execute('UPDATE cars SET fuel = ? WHERE id=?', (max_fuel, car_id))
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id=?', (cost, user_id))
        conn.commit()
        bot.send_message(call.message.chat.id, f"⛽ Заправлено {needed} л. Списанно {cost} ₽.")

def partial_fuel(message, car_id, price_per_liter):
    try:
        liters = float(message.text)
        if liters <= 0:
            bot.send_message(message.chat.id, "Некорректное значение.")
            return
        car = cursor.execute('SELECT fuel FROM cars WHERE id=?', (car_id,)).fetchone()
        max_fuel = 80
        new_fuel = min(max_fuel, car[0] + liters)
        actual_liters = new_fuel - car[0]
        cost = actual_liters * price_per_liter
        balance = cursor.execute('SELECT balance FROM users WHERE user_id=?', (message.from_user.id,)).fetchone()[0]
        if balance < cost:
            bot.send_message(message.chat.id, "Недостаточно средств.")
            return
        cursor.execute('UPDATE cars SET fuel = ? WHERE id=?', (new_fuel, car_id))
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id=?', (cost, message.from_user.id))
        conn.commit()
        bot.send_message(message.chat.id, f"⛽ Заправлено {actual_liters} л. Списанно {cost} ₽.")
    except ValueError:
        bot.send_message(message.chat.id, "Введите число.")

# Тюнинг (упрощённо)
@bot.callback_query_handler(func=lambda call: call.data == 'tune_car')
def tune_car(call):
    user_id = call.from_user.id
    car_id = cursor.execute('SELECT car_id FROM users WHERE user_id=?', (user_id,)).fetchone()[0]
    if not car_id:
        bot.answer_callback_query(call.id, "У вас нет машины!")
        return
    tuning_level = cursor.execute('SELECT tuning_level FROM cars WHERE id=?', (car_id,)).fetchone()[0]
    cost = (tuning_level + 1) * 50000  # стоимость тюнинга растёт
    balance = cursor.execute('SELECT balance FROM users WHERE user_id=?', (user_id,)).fetchone()[0]
    if balance < cost:
        bot.send_message(call.message.chat.id, "Недостаточно денег.")
        return
    cursor.execute('UPDATE cars SET tuning_level = tuning_level + 1 WHERE id=?', (car_id,))
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id=?', (cost, user_id))
    conn.commit()
    bot.send_message(call.message.chat.id, f"✅ Тюнинг выполнен! Уровень теперь {tuning_level+1}. Потрачено {cost} ₽.")

# Брак (упрощённо)
@bot.message_handler(func=lambda m: m.text == '💍 Брак')
def marriage_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Предложить брак", callback_data='propose'))
    markup.add(types.InlineKeyboardButton("Развод", callback_data='divorce'))
    bot.send_message(message.chat.id, "Семейные дела:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'propose')
def propose(call):
    bot.send_message(call.message.chat.id, "Введите ID пользователя, которому хотите предложить брак:")
    bot.register_next_step_handler(call.message, process_propose)

def process_propose(message):
    target_id = int(message.text)
    user_id = message.from_user.id
    if target_id == user_id:
        bot.send_message(message.chat.id, "Нельзя жениться на самом себе.")
        return
    # Проверяем, свободны ли оба
    user1 = cursor.execute('SELECT married_to FROM users WHERE user_id=?', (user_id,)).fetchone()
    user2 = cursor.execute('SELECT married_to FROM users WHERE user_id=?', (target_id,)).fetchone()
    if user1[0] or user2[0]:
        bot.send_message(message.chat.id, "Один из вас уже состоит в браке.")
        return
    # Здесь можно реализовать механизм принятия предложения, но для простоты сразу заключим брак
    cursor.execute('UPDATE users SET married_to=? WHERE user_id=?', (target_id, user_id))
    cursor.execute('UPDATE users SET married_to=? WHERE user_id=?', (user_id, target_id))
    conn.commit()
    bot.send_message(message.chat.id, f"Поздравляю! Вы в браке с {target_id}.")

@bot.callback_query_handler(func=lambda call: call.data == 'divorce')
def divorce(call):
    user_id = call.from_user.id
    spouse = cursor.execute('SELECT married_to FROM users WHERE user_id=?', (user_id,)).fetchone()[0]
    if not spouse:
        bot.answer_callback_query(call.id, "Вы не состоите в браке.")
        return
    cursor.execute('UPDATE users SET married_to=NULL WHERE user_id IN (?, ?)', (user_id, spouse))
    conn.commit()
    bot.send_message(call.message.chat.id, "Вы разведены.")

# Бизнес (заглушка)
@bot.message_handler(func=lambda m: m.text == '🏢 Бизнес')
def business(message):
    bot.send_message(message.chat.id, "Раздел бизнеса в разработке.")

# Обработка остальных сообщений
@bot.message_handler(func=lambda m: True)
def echo(message):
    bot.send_message(message.chat.id, "Используйте кнопки меню.")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()