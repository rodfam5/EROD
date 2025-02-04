from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    projects = db.relationship('Project', backref='client', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    contractor_id = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

# Routes
@app.route('/')
def index():
    clients = Client.query.all()
    return render_template('index.html', clients=clients)

@app.route('/clients', methods=['GET', 'POST'])
def manage_clients():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        new_client = Client(name=name, email=email, phone=phone, address=address)
        db.session.add(new_client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('manage_clients'))
    clients = Client.query.all()
    return render_template('clients.html', clients=clients)

@app.route('/clients/<int:client_id>/projects', methods=['GET', 'POST'])
def client_projects(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_project = Project(title=title, description=description, client_id=client.id)
        db.session.add(new_project)
        db.session.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('client_projects', client_id=client_id))
    projects = Project.query.filter_by(client_id=client_id).all()
    return render_template('client_projects.html', client=client, projects=projects)

@app.route('/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        client_id = int(request.form['client_id'])
        new_task = Task(title=title, description=description, due_date=due_date, client_id=client_id)
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('manage_tasks'))
    tasks = Task.query.all()
    clients = Client.query.all()
    return render_template('tasks.html', tasks=tasks, clients=clients)

@app.route('/notifications')
def notifications():
    user_id = 1  # Replace with the logged-in user ID
    notifications = Notification.query.filter_by(user_id=user_id).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/bids', methods=['GET', 'POST'])
def manage_bids():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        contractor_id = int(request.form['contractor_id'])
        project_id = int(request.form['project_id'])
        new_bid = Bid(amount=amount, contractor_id=contractor_id, project_id=project_id)
        db.session.add(new_bid)
        db.session.commit()
        flash('Bid submitted successfully!', 'success')
        return redirect(url_for('manage_bids'))
    bids = Bid.query.all()
    projects = Project.query.all()
    return render_template('bids.html', bids=bids, projects=projects)

@app.route('/clients/<int:client_id>/tasks', methods=['GET', 'POST'])
def client_tasks(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        new_task = Task(title=title, description=description, due_date=due_date, client_id=client_id)
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('client_tasks', client_id=client_id))
    tasks = Task.query.filter_by(client_id=client_id).all()
    return render_template('client_tasks.html', client=client, tasks=tasks)

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
``