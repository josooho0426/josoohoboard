from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'jshboard'


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

def get_db_connection():
    connection = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
    connection.close()
    if user:
        return User(user_id=user['id'], username=user['username'])
    return None

@app.route('/')
def index():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT p.id, p.title, p.author, u.username AS author_name
            FROM posts p
            JOIN users u ON p.author = u.id
            ORDER BY p.id DESC
        ''')
        posts = cursor.fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

@app.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        user_id = current_user.id
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
            connection.commit()
        connection.close()

        flash('Your account has been deleted.', 'success')
        logout_user()
        return redirect(url_for('index'))

    return render_template('delete_account.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        school = request.form['school']
        full_name = request.form['full_name'] 
        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO users (username, password, school, full_name) VALUES (%s, %s, %s, %s)', (username, hashed_password, school, full_name))
            connection.commit()
        connection.close()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT id, password FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
        
        connection.close()
        
        if user and check_password_hash(user['password'], password):
            user_obj = User(user_id=user['id'], username=username)
            login_user(user_obj)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = current_user.id

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO posts (title, content, author) VALUES (%s, %s, %s)', (title, content, author))
            connection.commit()
        connection.close()

        return redirect(url_for('index'))
    return render_template('post.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM posts WHERE id = %s AND author = %s', (id, current_user.id))
        post = cursor.fetchone()

    if post is None:
        flash('You do not have permission to edit this post.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        with connection.cursor() as cursor:
            cursor.execute('UPDATE posts SET title = %s, content = %s WHERE id = %s', (title, content, id))
            connection.commit()
        connection.close()
        flash('Post updated successfully.', 'success')
        return redirect(url_for('index'))
    connection.close()
    return render_template('edit.html', post=post)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM posts WHERE id = %s AND author = %s', (id, current_user.id))
        post = cursor.fetchone()

    if post is None:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('index'))

    with connection.cursor() as cursor:
        cursor.execute('DELETE FROM posts WHERE id = %s', (id,))
        connection.commit()
    connection.close()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/post/<int:id>')
def view_post(id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT p.id, p.title, p.content, u.username AS author_name
            FROM posts p
            JOIN users u ON p.author = u.id
            WHERE p.id = %s
        ''', (id,))
        post = cursor.fetchone()
    connection.close()
    return render_template('view_post.html', post=post)

if __name__ == '__main__':
    app.run(debug=True)
