from flask import Flask, render_template, request, json, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///platform.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'client', 'contractor', 'admin', 'project_manager', 'supplier'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# Initialize Database
def create_tables():
    with app.app_context():
        db.create_all()

create_tables()

# Home Route
@app.route('/')
def home():
    return render_template('index.html')

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password, role=role)

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return f"Error: {str(e)}"

    return render_template('register.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))

        return "Invalid username or password."

    return render_template('login.html')

# User Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'client':
        projects = Project.query.filter_by(client_id=session['user_id']).all()
    elif role == 'contractor':
        projects = Project.query.filter_by(contractor_id=session['user_id']).all()
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        projects = []

    return render_template('dashboard.html', projects=projects, role=role)

# Add Project
@app.route('/projects', methods=['POST'])
def add_project():
    if 'user_id' not in session or session['role'] != 'client':
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    new_project = Project(title=title, description=description, client_id=session['user_id'])

    try:
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Error: {str(e)}"

# Admin Dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    users = User.query.all()
    projects = Project.query.all()
    return render_template('admin_dashboard.html', users=users, projects=projects)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    try:
        app.run(debug=True, use_reloader=False)
    except ModuleNotFoundError as e:
        if "_multiprocessing" in str(e):
            print("Error: _multiprocessing module is not available. Ensure that your Python environment has all necessary system dependencies installed.")
        else:
            raise
