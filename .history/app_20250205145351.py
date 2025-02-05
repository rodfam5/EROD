from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import stripe
import json
import pdfkit
pdfkit_config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

from flask_babel import Babel
from apscheduler.schedulers.background import BackgroundScheduler
import openai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'fr', 'es']
babel = Babel(app)
db = SQLAlchemy(app)


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
    return render_template('index.html')

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

@app.route('/calculate_materials')
def calculate_materials():
    area = float(request.args.get("area", 0))
    total_material_cost = sum([cost_data["base_price"] * (area / 100) for cost_data in MATERIAL_COSTS.values()])
    total_labor_cost = sum([rate * (area / 1000) for rate in LABOR_COSTS.values()])
    return jsonify({
        "total_material_cost": total_material_cost,
        "total_labor_cost": total_labor_cost,
        "grand_total": total_material_cost + total_labor_cost
    })

@app.route('/export_estimation_pdf')
def export_estimation_pdf():
    html = render_template("estimation.html")
    pdf = pdfkit.from_string(html, False)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name="estimation_report.pdf")

@app.route('/generate_quote')
def generate_quote():
    html = render_template("estimation.html")
    pdf = pdfkit.from_string(html, False)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name="project_quote.pdf")

@app.route('/send_estimate_for_approval')
def send_estimate_for_approval():
    return jsonify({"message": "Estimate sent for approval!"})

@app.route('/enable_collaboration')
def enable_collaboration():
    return jsonify({"message": "Real-time collaboration enabled."})

@app.route('/finances')
def finances():
    invoices = Invoice.query.all()
    return render_template('finances.html', invoices=invoices)

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
                        'unit_amount': int(invoice.amount * 100),
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

# --- AI-Based Cost Prediction & Risk Assessment ---
@app.route('/predict_cost', methods=['POST'])
def predict_cost():
    data = request.json
    project_size = float(data['project_size'])
    predicted_cost = project_size * 120  # Example AI-driven formula
    return jsonify({"predicted_cost": predicted_cost})

# --- Automatic Tax & Compliance Calculations ---
@app.route('/calculate_tax', methods=['POST'])
def calculate_tax():
    data = request.json
    project_cost = float(data['project_cost'])
    tax_rate = 0.15  # Example tax calculation
    tax_amount = project_cost * tax_rate
    return jsonify({"tax_amount": tax_amount})

# --- AI-Powered Chatbot for Assistance ---
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

# --- Automated Scheduling & Gantt Chart Data API ---
@app.route('/schedule_project', methods=['POST'])
def schedule_project():
    data = request.json
    project_name = data['project_name']
    start_date = data['start_date']
    end_date = data['end_date']
    scheduler.add_job(func=lambda: print(f"Scheduled project {project_name}"), trigger='date', run_date=start_date)
    return jsonify({"message": f"Project {project_name} scheduled from {start_date} to {end_date}"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
