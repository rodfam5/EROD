from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)fla
    address = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Active')

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class AllianceMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/clients')
def clients():
    return render_template('clients.html')

@app.route('/client_detail')
def client_detail():
    return render_template('client_detail.html')

@app.route('/client_projects')
def client_projects():
    return render_template('client_projects.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/grants')
def grants():
    return render_template('grants.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

@app.route('/project_bids')
def project_bids():
    return render_template('project_bids.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/sales')
def sales_client_management():
    return render_template('sales_client_management.html')

@app.route('/tasks')
def tasks():
    return render_template('tasks.html')

@app.route('/alliances', methods=['GET', 'POST'])
def alliances():
    if request.method == 'POST':
        name = request.form['name']
        company = request.form['company']
        specialty = request.form['specialty']
        location = request.form['location']
        new_member = AllianceMember(name=name, company=company, specialty=specialty, location=location)
        db.session.add(new_member)
        db.session.commit()
        return redirect(url_for('alliances'))
    
    alliance_members = AllianceMember.query.all()
    return render_template('alliances.html', alliance_members=alliance_members)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
