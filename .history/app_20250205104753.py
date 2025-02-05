from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import stripe

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///construction_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

stripe.api_key = "your_stripe_secret_key_here"

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
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

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    due_date = db.Column(db.String(50), nullable=False)
    stripe_checkout_id = db.Column(db.String(100), nullable=True)

@app.route('/')
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
