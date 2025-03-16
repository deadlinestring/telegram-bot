import logging
import os
import psycopg2
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
DB_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключение к PostgreSQLrm -rf 
def get_db_connection():
    return psycopg2.connect(DB_URL)

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subcategories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            photo TEXT,
            subcategory_id INTEGER REFERENCES subcategories(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

# Получение списка категорий
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return categories

# Получение списка подкатегорий
def get_subcategories(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM subcategories WHERE category_id = %s', (category_id,))
    subcategories = cursor.fetchall()
    conn.close()
    return subcategories

# Получение списка товаров
def get_products(subcategory_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, description, photo FROM products WHERE subcategory_id = %s', (subcategory_id,))
    products = cursor.fetchall()
    conn.close()
    return products

# Получение ID категории по ID подкатегории
def get_category_id_by_subcategory(subcategory_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT category_id FROM subcategories WHERE id = %s', (subcategory_id,))
    category_id = cursor.fetchone()
    conn.close()
    return category_id[0] if category_id else None

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    categories = get_categories()
    keyboard = [[InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}")] for category in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите категорию:', reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("category_"):
        category_id = int(data.split("_")[1])
        subcategories = get_subcategories(category_id)
        if not subcategories:
            await query.edit_message_text(text="В этой категории пока нет подкатегорий.")
            return
        keyboard = [[InlineKeyboardButton(subcategory[1], callback_data=f"subcategory_{subcategory[0]}")] for subcategory in subcategories]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_categories")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Выберите подкатегорию:", reply_markup=reply_markup)
    elif data.startswith("subcategory_"):
        subcategory_id = int(data.split("_")[1])
        products = get_products(subcategory_id)
        if not products:
            await query.edit_message_text(text="В этой подкатегории пока нет товаров.")
            return
        product = products[0]
        keyboard = [[InlineKeyboardButton("Следующий товар", callback_data=f"next_{subcategory_id}_0")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_media(media=InputMediaPhoto(media=product[3], caption=f"{product[1]}\n{product[2]}"), reply_markup=reply_markup)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    📌 Доступные команды:
    /start - Начать работу
    /help - Список команд
    """
    await update.message.reply_text(help_text)

# Обработчик ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f'Ошибка: {context.error}')
    if ADMIN_ID:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"❗ Ошибка: {context.error}")

def main() -> None:
    init_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))

    application.add_error_handler(error)

    application.run_polling()

if __name__ == '__main__':
    main()


    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
