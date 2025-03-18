import os
import secrets
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
import subprocess
import logging
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

# Генерация случайного секретного ключа (32 символа)
app.secret_key = secrets.token_hex(16)

# Логирование
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Путь к базе данных
DATABASE = 'users.db'

# Функция для подключения к базе данных SQLite
def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn
    
# Функция для создания таблицы пользователей
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Создание таблицы, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Хешируем пароль для стандартного пользователя
    hashed_password = generate_password_hash("admin123")  # Хешируем стандартный пароль

    # Добавление стандартного пользователя, если его нет
    cursor.execute('''
        INSERT INTO users (username, password) 
        SELECT "admin", ?
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = "admin");
    ''', (hashed_password,))  # Передаем хешированный пароль
    conn.commit()
    conn.close()

# Вызов функции для создания таблицы при старте приложения
init_db()

# Функция для авторизации
def check_user(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):  # user[2] — это хеш пароля
        return user
    return None

# Функция для получения списка пользователей через командный интерфейс Vikunja
def get_users():
    try:
        cmd = "vikunja user list"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            users = result.stdout.splitlines()

            user_list = []
            for user in users[5:]:
                if user.strip() and not user.startswith("INFO ▶") and not user.startswith("+") and not user.startswith("| ID"):
                    user = user.strip()
                    user_data = user.split('|')
                    user_data = [item.strip() for item in user_data if item.strip()]

                    if len(user_data) >= 5:
                        user_list.append({
                            "id": user_data[0],
                            "username": user_data[1],
                            "email": user_data[2],
                            "status": user_data[3],
                            "created": user_data[4],
                        })

            return user_list
        else:
            return []
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# Маршрут для авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Проверка пользователя
        user = check_user(username, password)
        if user:
            session['user_id'] = user[0]  # Сохраняем id пользователя в сессии
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'danger')
    
    return render_template('login.html')

# Страница выхода
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))
# новый маршрут /change-password, который обрабатывает форму для смены пароля и обновляет его в базе данных
@app.route('/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    new_password = request.form['new_password']
    hashed_password = generate_password_hash(new_password)  # Хешируем новый пароль

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, session['user_id']))
        conn.commit()
        conn.close()

        flash('Пароль успешно изменён!', 'success')
    except Exception as e:
        flash(f'Ошибка при смене пароля: {e}', 'danger')

    return redirect(url_for('index'))
    
# Главная страница (получение списка пользователей)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Получаем информацию о текущем пользователе
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (session['user_id'],))
    current_user = cursor.fetchone()
    conn.close()

    users = get_users()
    return render_template('index.html', users=users, current_user=current_user)

# Маршрут для создания нового пользователя
@app.route('/create', methods=['POST'])
def create():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    create_user(username, email, password)

    return redirect(url_for('index'))

# Функция для создания нового пользователя через командный интерфейс Vikunja
def create_user(username, email, password):
    try:
        cmd = f"vikunja user create --username {username} --email {email} --password {password}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            logging.info(f"Пользователь {username} успешно создан!")
        else:
            logging.error(f"Ошибка при создании пользователя: {result.stderr}")
    except Exception as e:
        logging.error(f"Ошибка: {e}")

# Маршрут для удаления пользователя
@app.route('/delete/<int:user_id>', methods=['POST'])
def delete(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    delete_user(user_id)
    return redirect(url_for('index'))

# Функция для удаления пользователя через командный интерфейс Vikunja
def delete_user(user_id):
    try:
        cmd = f"vikunja user delete {user_id} --now --confirm"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            logging.info(f"Пользователь с ID {user_id} успешно удален!")
        else:
            logging.error(f"Ошибка при удалении пользователя с ID {user_id}: {result.stderr}")
    except Exception as e:
        logging.error(f"Ошибка при удалении: {e}")

# Функция для сброса пароля пользователя
@app.route('/reset-password/<int:user_id>', methods=['POST'])
def reset_password(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_password = request.form['new_password']  # Новый пароль из формы
    try:
        cmd = f"vikunja user reset-password {user_id} --password {new_password} --direct"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info(f"Пароль для пользователя с ID {user_id} был сброшен.")
            flash(f"Пароль для пользователя с ID {user_id} был сброшен.", "success")
        else:
            logging.error(f"Ошибка при сбросе пароля для пользователя с ID {user_id}: {result.stderr}")
            flash(f"Ошибка при сбросе пароля: {result.stderr}", "danger")
        
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        flash(f"Ошибка при сбросе пароля: {e}", "danger")
        return redirect(url_for('index'))

# Маршрут для обновления данных пользователя
@app.route('/update/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    username = request.form['username']
    email = request.form['email']
    
    try:
        cmd = f"vikunja user update {user_id} --username {username} --email {email}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            flash(f"Данные пользователя с ID {user_id} успешно обновлены.", "success")
        else:
            flash(f"Ошибка при обновлении данных пользователя с ID {user_id}: {result.stderr}", "danger")
        
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        flash(f"Ошибка при обновлении данных: {e}", "danger")
        return redirect(url_for('index'))

# Маршрут для отключения пользователя
@app.route('/change-status/<int:user_id>/disable', methods=['POST'])
def disable_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        cmd = f"vikunja user change-status {user_id} --disable"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            logging.info(f"Пользователь с ID {user_id} успешно отключен!")
            flash(f"Пользователь с ID {user_id} успешно отключен.", "success")
        else:
            logging.error(f"Ошибка при отключении пользователя с ID {user_id}: {result.stderr}")
            flash(f"Ошибка при отключении пользователя: {result.stderr}", "danger")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        flash(f"Ошибка при отключении пользователя: {e}", "danger")
    
    return redirect(url_for('index'))

# Маршрут для включения пользователя
@app.route('/change-status/<int:user_id>/enable', methods=['POST'])
def enable_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        cmd = f"vikunja user change-status {user_id} --enable"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            logging.info(f"Пользователь с ID {user_id} успешно включен!")
            flash(f"Пользователь с ID {user_id} успешно включен.", "success")
        else:
            logging.error(f"Ошибка при включении пользователя с ID {user_id}: {result.stderr}")
            flash(f"Ошибка при включении пользователя: {result.stderr}", "danger")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        flash(f"Ошибка при включении пользователя: {e}", "danger")
    
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
