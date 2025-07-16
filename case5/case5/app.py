from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret_key'

DATABASE = 'travel_diary.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            cost REAL,
            places TEXT,
            heritage_places TEXT,
            date_from TEXT,
            date_to TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return redirect(url_for('tours'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login_ = request.form.get('login')
        password = request.form.get('password')
        if not login_ or not password:
            flash('Логин и пароль обязательны.')
            return render_template('register.html')
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (login, password_hash) VALUES (?, ?)",
                (login_, generate_password_hash(password))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Пользователь с таким логином уже существует.')
            return render_template('register.html')
        finally:
            conn.close()
        flash('Регистрация успешна. Войдите в систему.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_ = request.form.get('login')
        password = request.form.get('password')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE login = ?", (login_,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_login'] = user['login']
            return redirect(url_for('my_tours'))
        else:
            flash('Неверный логин или пароль.')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/tours')
def tours():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tours.*, users.login FROM tours 
        JOIN users ON tours.user_id = users.id
        ORDER BY tours.id DESC
    ''')
    tours = cursor.fetchall()
    conn.close()
    return render_template('tours.html', tours=tours)

@app.route('/my_tours')
@login_required
def my_tours():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tours WHERE user_id = ? ORDER BY id DESC', (user_id,))
    tours = cursor.fetchall()
    conn.close()
    return render_template('my_tours.html', tours=tours)

@app.route('/tours/new', methods=['GET', 'POST'])
@login_required
def new_tour():
    if request.method == 'POST':
        title = request.form.get('title')
        cost = request.form.get('cost')
        places = request.form.get('places')
        heritage_places = request.form.get('heritage_places')
        date_from = request.form.get('date_from')
        date_to = request.form.get('date_to')
        
        if not title:
            flash('Название тура обязательно.')
            return render_template('new_tour.html')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tours 
            (user_id, title, cost, places, heritage_places, date_from, date_to) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], title, cost, places, heritage_places, date_from, date_to))
        conn.commit()
        conn.close()
        return redirect(url_for('my_tours'))
    return render_template('new_tour.html')

@app.route('/tours/<int:tour_id>')
def tour_detail(tour_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tours.*, users.login FROM tours 
        JOIN users ON tours.user_id = users.id
        WHERE tours.id = ?
    ''', (tour_id,))
    tour = cursor.fetchone()
    conn.close()
    if tour is None:
        return "Тур не найден", 404
    return render_template('tour_detail.html', tour=tour)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
