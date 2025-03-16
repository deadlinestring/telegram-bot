import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            photo TEXT,
            subcategory_id INTEGER,
            FOREIGN KEY (subcategory_id) REFERENCES subcategories (id)
        )
    ''')
    conn.commit()
    conn.close()

# Получение списка категорий
def get_categories():
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return categories

# Получение списка подкатегорий
def get_subcategories(category_id):
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM subcategories WHERE category_id = ?', (category_id,))
    subcategories = cursor.fetchall()
    conn.close()
    return subcategories

# Получение списка товаров
def get_products(subcategory_id):
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, description, photo FROM products WHERE subcategory_id = ?', (subcategory_id,))
    products = cursor.fetchall()
    conn.close()
    return products

# Команда /start
async def start(update: Update, context: CallbackContext) -> None:
    categories = get_categories()
    keyboard = [[InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}")] for category in categories]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Пожалуйста, выберите категорию:', reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("category_"):  # Если это категория
        category_id = int(data.split("_")[1])
        subcategories = get_subcategories(category_id)
        keyboard = [[InlineKeyboardButton(subcategory[1], callback_data=f"subcategory_{subcategory[0]}")] for subcategory in subcategories]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_categories")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Выберите подкатегорию:", reply_markup=reply_markup)
    elif data.startswith("subcategory_"):  # Если это подкатегория
        subcategory_id = int(data.split("_")[1])
        products = get_products(subcategory_id)
        if products:
            product = products[0]  # Показываем первый товар
            keyboard = [
                [InlineKeyboardButton("Следующий товар", callback_data=f"next_{subcategory_id}_0")],
                [InlineKeyboardButton("Назад", callback_data=f"category_{get_category_id_by_subcategory(subcategory_id)}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_media(media=InputMediaPhoto(media=product[3], caption=f"{product[1]}\n{product[2]}"), reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="В этой подкатегории пока нет товаров.")
    elif data.startswith("next_"):  # Переключение между товарами
        _, subcategory_id, index = data.split("_")
        subcategory_id, index = int(subcategory_id), int(index)
        products = get_products(subcategory_id)
        if index + 1 < len(products):
            product = products[index + 1]
            keyboard = [
                [InlineKeyboardButton("Следующий товар", callback_data=f"next_{subcategory_id}_{index + 1}")],
                [InlineKeyboardButton("Назад", callback_data=f"category_{get_category_id_by_subcategory(subcategory_id)}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_media(media=InputMediaPhoto(media=product[3], caption=f"{product[1]}\n{product[2]}"), reply_markup=reply_markup)
        else:
            await query.answer("Это последний товар в списке.")
    elif data == "back_to_categories":  # Возврат к категориям
        categories = get_categories()
        keyboard = [[InlineKeyboardButton(category[1], callback_data=f"category_{category[0]}")] for category in categories]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Пожалуйста, выберите категорию:", reply_markup=reply_markup)

# Поиск по ключевым словам
async def search(update: Update, context: CallbackContext) -> None:
    search_term = update.message.text.lower()
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, p.description, c.name, s.name
        FROM products p
        JOIN subcategories s ON p.subcategory_id = s.id
        JOIN categories c ON s.category_id = c.id
        WHERE p.name LIKE ? OR p.description LIKE ?
    ''', (f"%{search_term}%", f"%{search_term}%"))
    results = cursor.fetchall()
    conn.close()
    if results:
        response = "\n".join([f"{row[2]} -> {row[3]} -> {row[0]}: {row[1]}" for row in results])
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Ничего не найдено.")

# Добавление новой категории
async def add_category(update: Update, context: CallbackContext) -> None:
    category_name = " ".join(context.args)
    if category_name:
        conn = sqlite3.connect('catalog.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Категория '{category_name}' добавлена.")
    else:
        await update.message.reply_text("Используйте: /add_category <название категории>")

# Добавление новой подкатегории
async def add_subcategory(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Используйте: /add_subcategory <категория> <название подкатегории>")
        return
    category_name, subcategory_name = context.args[0], " ".join(context.args[1:])
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
    category_id = cursor.fetchone()
    if category_id:
        cursor.execute('INSERT INTO subcategories (name, category_id) VALUES (?, ?)', (subcategory_name, category_id[0]))
        conn.commit()
        await update.message.reply_text(f"Подкатегория '{subcategory_name}' добавлена в категорию '{category_name}'.")
    else:
        await update.message.reply_text("Категория не найдена.")
    conn.close()

# Добавление нового товара
async def add_product(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 4:
        await update.message.reply_text("Используйте: /add_product <категория> <подкатегория> <название> <описание> <фото>")
        return
    category_name, subcategory_name, product_name, description, photo = context.args[0], context.args[1], context.args[2], " ".join(context.args[3:-1]), context.args[-1]
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
    category_id = cursor.fetchone()
    if category_id:
        cursor.execute('SELECT id FROM subcategories WHERE name = ? AND category_id = ?', (subcategory_name, category_id[0]))
        subcategory_id = cursor.fetchone()
        if subcategory_id:
            cursor.execute('INSERT INTO products (name, description, photo, subcategory_id) VALUES (?, ?, ?, ?)', (product_name, description, photo, subcategory_id[0]))
            conn.commit()
            await update.message.reply_text(f"Товар '{product_name}' добавлен в {category_name} -> {subcategory_name}.")
        else:
            await update.message.reply_text("Подкатегория не найдена.")
    else:
        await update.message.reply_text("Категория не найдена.")
    conn.close()

# Удаление категории
async def delete_category(update: Update, context: CallbackContext) -> None:
    category_name = " ".join(context.args)
    if category_name:
        conn = sqlite3.connect('catalog.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM categories WHERE name = ?', (category_name,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Категория '{category_name}' удалена.")
    else:
        await update.message.reply_text("Используйте: /delete_category <название категории>")

# Удаление подкатегории
async def delete_subcategory(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Используйте: /delete_subcategory <категория> <название подкатегории>")
        return
    category_name, subcategory_name = context.args[0], " ".join(context.args[1:])
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
    category_id = cursor.fetchone()
    if category_id:
        cursor.execute('DELETE FROM subcategories WHERE name = ? AND category_id = ?', (subcategory_name, category_id[0]))
        conn.commit()
        await update.message.reply_text(f"Подкатегория '{subcategory_name}' удалена из категории '{category_name}'.")
    else:
        await update.message.reply_text("Категория не найдена.")
    conn.close()

# Удаление товара
async def delete_product(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        await update.message.reply_text("Используйте: /delete_product <категория> <подкатегория> <название товара>")
        return
    category_name, subcategory_name, product_name = context.args[0], context.args[1], " ".join(context.args[2:])
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
    category_id = cursor.fetchone()
    if category_id:
        cursor.execute('SELECT id FROM subcategories WHERE name = ? AND category_id = ?', (subcategory_name, category_id[0]))
        subcategory_id = cursor.fetchone()
        if subcategory_id:
            cursor.execute('DELETE FROM products WHERE name = ? AND subcategory_id = ?', (product_name, subcategory_id[0]))
            conn.commit()
            await update.message.reply_text(f"Товар '{product_name}' удален из {category_name} -> {subcategory_name}.")
        else:
            await update.message.reply_text("Подкатегория не найдена.")
    else:
        await update.message.reply_text("Категория не найдена.")
    conn.close()

# Получение ID категории по ID подкатегории
def get_category_id_by_subcategory(subcategory_id):
    conn = sqlite3.connect('catalog.db')
    cursor = conn.cursor()
    cursor.execute('SELECT category_id FROM subcategories WHERE id = ?', (subcategory_id,))
    category_id = cursor.fetchone()
    conn.close()
    return category_id[0] if category_id else None

# Обработчик ошибок
async def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def main() -> None:
    # Инициализация базы данных
    init_db()

    # Вставьте сюда ваш токен
    application = Application.builder().token("7824343407:AAFrCOOvjFllY5lTGWANx3739thqw21BsTE").build()

    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    application.add_handler(CommandHandler("add_category", add_category))
    application.add_handler(CommandHandler("add_subcategory", add_subcategory))
    application.add_handler(CommandHandler("add_product", add_product))
    application.add_handler(CommandHandler("delete_category", delete_category))
    application.add_handler(CommandHandler("delete_subcategory", delete_subcategory))
    application.add_handler(CommandHandler("delete_product", delete_product))

    # Регистрируем обработчик ошибок
    application.add_error_handler(error)

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()