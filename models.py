from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Employee(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    must_change_password = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Exercice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)  # <-- LIÉ AU SALARIE
    
    employee = db.relationship('Employee', backref=db.backref('exercices', lazy=True, cascade='all, delete-orphan'))

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    exercice_id = db.Column(db.Integer, db.ForeignKey('exercice.id', ondelete='CASCADE'), nullable=False)
    firstname = db.Column(db.String(100), nullable=False)

class EmpData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    exercice_id = db.Column(db.Integer, db.ForeignKey('exercice.id', ondelete='CASCADE'), nullable=False)
    rfr = db.Column(db.Float, default=0.0)
    en_couple = db.Column(db.Boolean, default=False)
    parent_isole = db.Column(db.Boolean, default=False)

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    exercice_id = db.Column(db.Integer, db.ForeignKey('exercice.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(50), nullable=False) # 'location', 'sport', 'colo'
    label = db.Column(db.String(200), nullable=True)
    amount_invoiced = db.Column(db.Float, nullable=False)
    amount_subsidized = db.Column(db.Float, nullable=False)
    beneficiary = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.String(20), nullable=True)
    end_date = db.Column(db.String(20), nullable=True)
    date = db.Column(db.String(20), nullable=True)
    invoice_file = db.Column(db.String(200), nullable=True)
    form_file = db.Column(db.String(200), nullable=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    taux_sport = db.Column(db.Float, default=50.0)
    plafond_base_location = db.Column(db.Float, default=300.0)
    plafond_max_location = db.Column(db.Float, default=750.0)
    majoration_loc_enfant = db.Column(db.Float, default=40.0)