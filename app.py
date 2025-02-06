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

# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Stripe & OpenAI Setup ---
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
    client_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    size_sqft = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    due_date = db.Column(db.String(50), nullable=False)
    stripe_checkout_id = db.Column(db.String(100), nullable=True)

# --- Material & Labor Cost Data ---
MATERIAL_COSTS = {
    "concrete": {"base_price": 100, "unit": "cubic yard"},
    "steel": {"base_price": 200, "unit": "ton"},
    "wood": {"base_price": 50, "unit": "cubic foot"},
    "paint": {"base_price": 30, "unit": "gallon"}
}

LABOR_COSTS = {
    "carpenter": 35,
    "electrician": 50,
    "plumber": 45,
    "general_worker": 25
}

# --- Routes ---
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

@app.route('/clients')
def clients():
    return render_template('clients.html')

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/finances')
def finances():
    invoices = Invoice.query.all()
    return render_template('finances.html', invoices=invoices)

@app.route('/estimations', methods=['GET', 'POST'])
def estimations():
    estimated_cost = None
    suggested_materials = []
    if request.method == 'POST':
        project_size = float(request.form['project_size'])
        suggested_materials = [
            {"name": material, "quantity": round((cost_data["base_price"] * (project_size / 100)), 2), 
             "unit_cost": cost_data["base_price"], "total_cost": round((cost_data["base_price"] * (project_size / 100)), 2)}
            for material, cost_data in MATERIAL_COSTS.items()
        ]
        estimated_labor_cost = sum([rate * (project_size / 1000) for rate in LABOR_COSTS.values()])
        estimated_cost = sum(item["total_cost"] for item in suggested_materials) + estimated_labor_cost

    return render_template('estimation.html', estimated_cost=estimated_cost, estimated_materials=suggested_materials)

@app.route('/tasks')
def tasks():
    return render_template('tasks.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/sales')
def sales_client_management():
    return render_template('sales_client_management.html')

@app.route('/contract_management')
def contract_management():
    return render_template('contract_management.html')

@app.route('/team_management')
def team_management():
    return render_template('team_management.html')

@app.route('/alliances')
def alliances():
    return render_template('alliances.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/pay_invoice/<int:invoice_id>')
def pay_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if invoice and invoice.status == 'Pending':
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': f"Invoice #{invoice.id}"},
                        'unit_amount': int(invoice.amount * 100),  # Stripe expects amount in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('payment_success', invoice_id=invoice.id, _external=True),
                cancel_url=url_for('finances', _external=True),
            )
            invoice.stripe_checkout_id = checkout_session.id
            db.session.commit()
            return redirect(checkout_session.url)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return redirect(url_for('finances'))


@app.route('/payment_success/<int:invoice_id>')
def payment_success(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if invoice:
        invoice.status = 'Paid'
        db.session.commit()
    return redirect(url_for('finances'))

# --- AI & Chatbot Features ---
@app.route('/predict_cost', methods=['POST'])
def predict_cost():
    data = request.json
    project_size = float(data['project_size'])
    predicted_cost = project_size * 120
    return jsonify({"predicted_cost": predicted_cost})

@app.route('/calculate_tax', methods=['POST'])
def calculate_tax():
    data = request.json
    project_cost = float(data['project_cost'])
    tax_amount = project_cost * 0.15
    return jsonify({"tax_amount": tax_amount})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_message = request.json.get("message")
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Client: {user_message}\nAI:",
        max_tokens=100
    )
    return jsonify({"response": response['choices'][0]['text'].strip()})

# --- Multi-Language Support ---
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        request.accept_languages = lang
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
