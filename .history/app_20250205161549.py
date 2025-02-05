from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import stripe
import json
import pdfkit
from flask_babel import Babel
from apscheduler.schedulers.background import BackgroundScheduler
import openai
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'fr', 'es']
babel = Babel(app)
db = SQLAlchemy(app)

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- User Model for Flask-Login ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

stripe.api_key = "your_stripe_secret_key_here"
openai.api_key = "your_openai_api_key_here"
scheduler = BackgroundScheduler()
scheduler.start()

# --- Database Models ---
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Active')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    size_sqft = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    due_date = db.Column(db.String(50), nullable=False)
    stripe_checkout_id = db.Column(db.String(100), nullable=True)

# --- Index Route with Fixed Data Serialization ---
@app.route('/')
def index():
    projects = Project.query.all()
    
    projects_data = {
        "labels": [project.name for project in projects],
        "values": [project.size_sqft for project in projects]
    }

    tasks_data = {"labels": [], "values": []}  # Placeholder for tasks
    specialty_data = {"labels": [], "values": []}  # Placeholder for specialty
    location_data = {"labels": [], "values": []}  # Placeholder for locations

    return render_template(
        'index.html',
        total_clients=Client.query.count(),
        total_projects=len(projects),
        total_alliance_members=0,  # Update with alliance members
        projects_data=json.dumps(projects_data),
        tasks_data=json.dumps(tasks_data),
        specialty_data=json.dumps(specialty_data),
        location_data=json.dumps(location_data)
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
