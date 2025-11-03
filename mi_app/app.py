from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

# ------------------------------
# Inicialización
# ------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mi_clave_super_secreta_123'  # Cambia esto en producción
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ------------------------------
# Modelos
# ------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Note {self.title}>'

with app.app_context():
    db.create_all()

# ------------------------------
# Login manager
# ------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------------
# Rutas de usuarios
# ------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash("Email ya registrado", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Usuario registrado correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Has iniciado sesión correctamente.", "success")
            return redirect(url_for('home'))
        flash("Email o contraseña incorrectos.", "danger")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for('login'))

# ------------------------------
# Rutas de notas
# ------------------------------
@app.route('/')
@login_required
def home():
    sort_by = request.args.get('sort', 'date')
    query = request.args.get('q', '')
    color_options = ['#FFEB3B', '#FFCDD2', '#BBDEFB', '#C8E6C9', '#E1BEE7']

    notes_query = Note.query.filter_by(user_id=current_user.id)
    if query:
        notes_query = notes_query.filter(
            (Note.title.contains(query)) |
            (Note.content.contains(query)) |
            (Note.tags.contains(query))
        )

    if sort_by == 'title':
        notes = notes_query.order_by(Note.title.asc()).all()
    else:
        notes = notes_query.order_by(Note.created_at.desc()).all()

    note_colors = {note.id: random.choice(color_options) for note in notes}
    return render_template('index.html', notes=notes, note_colors=note_colors, sort_by=sort_by)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_note():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        tags = request.form.get('tags', '')
        new_note = Note(title=title, content=content, tags=tags, user_id=current_user.id)
        db.session.add(new_note)
        db.session.commit()
        flash("Nota agregada correctamente.", "success")
        return redirect(url_for('home'))
    return render_template('add_note.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_note(id):
    note = Note.query.get_or_404(id)
    if note.user_id != current_user.id:
        flash("No tienes permiso para editar esta nota.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        note.title = request.form['title']
        note.content = request.form['content']
        note.tags = request.form.get('tags', '')
        db.session.commit()
        flash("Nota actualizada correctamente.", "success")
        return redirect(url_for('home'))
    return render_template('edit_note.html', note=note)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_note(id):
    note = Note.query.get_or_404(id)
    if note.user_id != current_user.id:
        flash("No tienes permiso para eliminar esta nota.", "danger")
        return redirect(url_for('home'))

    db.session.delete(note)
    db.session.commit()
    flash("Nota eliminada correctamente.", "success")
    return redirect(url_for('home'))

# ------------------------------
# Run
# ------------------------------
import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)