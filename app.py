import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sk_live_xTikAtZjTBaWmCSQWYIz9eXVOtPXCl6V'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/bdd/ce_database.db'
app.config['UPLOAD_FOLDER'] = '/app/upload'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

os.makedirs('/app/data', exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def generate_uuid():
    return str(uuid.uuid4())

# ================= MODELS =================
class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    employee = db.relationship('Employee', backref='user', uselist=False, cascade="all, delete-orphan")

class Employee(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    
    exercices = db.relationship('Exercice', backref='employee', cascade="all, delete-orphan")

class Exercice(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    employee_id = db.Column(db.String(36), db.ForeignKey('employee.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    children = db.relationship('Child', backref='exercice', cascade="all, delete-orphan")
    emp_data = db.relationship('EmpData', backref='exercice', uselist=False, cascade="all, delete-orphan")
    requests = db.relationship('Request', backref='exercice', cascade="all, delete-orphan")

class Child(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    exercice_id = db.Column(db.String(36), db.ForeignKey('exercice.id'), nullable=False)
    firstname = db.Column(db.String(100), nullable=False)

class EmpData(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    exercice_id = db.Column(db.String(36), db.ForeignKey('exercice.id'), nullable=False)
    rfr = db.Column(db.Float, default=0.0)
    en_couple = db.Column(db.Boolean, default=False)
    parent_isole = db.Column(db.Boolean, default=False)

class Request(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    exercice_id = db.Column(db.String(36), db.ForeignKey('exercice.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False) # 'location', 'sport', 'colo'
    label = db.Column(db.String(200), nullable=True)
    amount_invoiced = db.Column(db.Float, nullable=False)
    amount_subsidized = db.Column(db.Float, default=0.0)
    beneficiary = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(50), nullable=True)
    end_date = db.Column(db.String(50), nullable=True)
    invoice_file = db.Column(db.String(200), nullable=True)

class GlobalSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))

# ================= HELPERS & BUSINESS LOGIC =================
def calculate_parts(emp_data, children_count):
    if not emp_data:
        return 1.0          
    
    parts = 2.0 if emp_data.en_couple else 1.0          

    if children_count == 1:
        if emp_data.parent_isole:
            parts += 1.0  # 1 part entière pour le 1er enfant d'un parent isolé (total 2.0 parts)
        else:
            parts += 0.5  # 0,5 part pour un célibataire sans majoration (total 1,5 part)
            
    elif children_count == 2:
        parts += 1.0      # 0,5 pour le 1er + 0,5 pour le 2e (ou majoration parent isolé incluant le 1er) -> Total 2,0 parts (célibataire) ou 2,5 parts (parent isolé)
        if emp_data.parent_isole:
            parts += 0.5  # Ajustement pour parent isolé avec 2 enfants (total 3,0 parts)
            
    elif children_count >= 3:
        # 1 part pour les deux premiers enfants, puis 1 part par enfant supplémentaire
        parts += 1.0 + (children_count - 2) * 1.0
        if emp_data.parent_isole:
            parts += 0.5  # Demi-part supplémentaire spécifique au parent isolé

    return parts

def get_subsidy_rate(rfr_total, parts, settings):
    try:
        s1 = float(settings.get('seuil_1', 10849.0))
        s2 = float(settings.get('seuil_2', 14291.0))
        s3 = float(settings.get('seuil_3', 16987.0))
        s4 = float(settings.get('seuil_4', 20351.0))
        s5 = float(settings.get('seuil_5', 23754.0))
    except ValueError:
        s1, s2, s3, s4, s5 = 10849.0, 14291.0, 16987.0, 20351.0, 23754.0

    limit_1 = s1 * parts
    limit_2 = s2 * parts
    limit_3 = s3 * parts
    limit_4 = s4 * parts
    limit_5 = s5 * parts

    if rfr_total <= limit_1:
        return 65
    elif rfr_total <= limit_2:
        return 55
    elif rfr_total <= limit_3:
        return 45
    elif rfr_total <= limit_4:
        return 35
    elif rfr_total <= limit_5:
        return 25
    else:
        return 20

def get_subsidy_details(rfr_total, parts, children_count, settings):
    try:
        s1 = float(settings.get('seuil_1', 10849.0))
        s2 = float(settings.get('seuil_2', 14291.0))
        s3 = float(settings.get('seuil_3', 16987.0))
        s4 = float(settings.get('seuil_4', 20351.0))
        s5 = float(settings.get('seuil_5', 23754.0))
        
        p1 = float(settings.get('plafond_t1', 750.0))
        p2 = float(settings.get('plafond_t2', 700.0))
        p3 = float(settings.get('plafond_t3', 650.0))
        p4 = float(settings.get('plafond_t4', 500.0))
        p5 = float(settings.get('plafond_t5', 350.0))
        p6 = float(settings.get('plafond_t6', 300.0))
        
        maj = float(settings.get('majoration_enfant', 40.0))
    except ValueError:
        s1, s2, s3, s4, s5 = 10849.0, 14291.0, 16987.0, 20351.0, 23754.0
        p1, p2, p3, p4, p5, p6 = 750.0, 700.0, 650.0, 500.0, 350.0, 300.0
        maj = 40.0

    limit_1 = s1 * parts
    limit_2 = s2 * parts
    limit_3 = s3 * parts
    limit_4 = s4 * parts
    limit_5 = s5 * parts

    if rfr_total <= limit_1:
        rate = 65
        base_plafond = p1
    elif rfr_total <= limit_2:
        rate = 55
        base_plafond = p2
    elif rfr_total <= limit_3:
        rate = 45
        base_plafond = p3
    elif rfr_total <= limit_4:
        rate = 35
        base_plafond = p4
    elif rfr_total <= limit_5:
        rate = 25
        base_plafond = p5
    else:
        rate = 20
        base_plafond = p6

    final_plafond_loc = base_plafond + (children_count * maj)
    return rate, final_plafond_loc

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Helper de contrôle de propriété
def can_access_employee(employee_id):
    if current_user.is_admin:
        return True
    return current_user.employee and current_user.employee.id == employee_id

# ================= ROUTES =================
@app.route('/')
@login_required
def index():
    if current_user.is_admin:
        employees = Employee.query.all()
        emp_id = request.args.get('emp_id', type=str)
        if not emp_id and employees:
            current_emp = employees[0]
        else:
            current_emp = Employee.query.get(emp_id) if emp_id else None
    else:
        current_emp = current_user.employee
        employees = [current_emp] if current_emp else []

    current_ex = None
    current_children = []
    emp_data = None
    parts = 1.0
    rate = 0
    plafond_loc = 500.0
    plafond_sport = 200.0
    reqs_loc, reqs_sport, reqs_colo = [], [], []
    cons_loc, cons_sport, cons_colo = 0.0, 0.0, 0.0
    exercices = []

    if current_emp:
        exercices = Exercice.query.filter_by(employee_id=current_emp.id).order_by(Exercice.year.desc()).all()
        current_year = 2026
        if not any(ex.year == current_year for ex in exercices):
            new_ex = Exercice(employee_id=current_emp.id, year=current_year)
            db.session.add(new_ex)
            db.session.commit()
            emp_data_init = EmpData(exercice_id=new_ex.id, rfr=0.0, en_couple=False, parent_isole=False)
            db.session.add(emp_data_init)
            db.session.commit()
            exercices = Exercice.query.filter_by(employee_id=current_emp.id).order_by(Exercice.year.desc()).all()

        ex_id = request.args.get('ex_id', type=str)
        if ex_id:
            current_ex = Exercice.query.filter_by(id=ex_id, employee_id=current_emp.id).first()
        elif exercices:
            current_ex = exercices[0]

        if current_ex:
            current_children = Child.query.filter_by(exercice_id=current_ex.id).all()
            emp_data = EmpData.query.filter_by(exercice_id=current_ex.id).first()
            if not emp_data:
                emp_data = EmpData(exercice_id=current_ex.id, rfr=0, en_couple=False, parent_isole=False)
                db.session.add(emp_data)
                db.session.commit()

            # Récupération sécurisée des paramètres globaux
            raw_settings = {s.key: s.value for s in GlobalSettings.query.all()}
            parts = calculate_parts(emp_data, len(current_children))
            rate, plafond_loc = get_subsidy_details(emp_data.rfr, parts, len(current_children), raw_settings)

            # Paramètres Sport & Culture
            sub_salarie = float(raw_settings.get('sport_salarie', 200.0))
            sub_conjoint = float(raw_settings.get('sport_conjoint', 100.0))
            sub_enfant = float(raw_settings.get('sport_enfant', 100.0))

            # Calcul du plafond global Sport & Culture
            plafond_sport = sub_salarie
            if emp_data and emp_data.en_couple:
                plafond_sport += sub_conjoint
            plafond_sport += len(current_children) * sub_enfant

            reqs_loc = Request.query.filter_by(exercice_id=current_ex.id, category='location').all()
            reqs_sport = Request.query.filter_by(exercice_id=current_ex.id, category='sport').all()
            reqs_colo = Request.query.filter_by(exercice_id=current_ex.id, category='colo').all()

            cons_loc = sum(r.amount_subsidized for r in reqs_loc)
            cons_sport = sum(r.amount_subsidized for r in reqs_sport)
            cons_colo = sum(r.amount_subsidized for r in reqs_colo)

    return render_template('index.html',
                           employees=employees,
                           current_emp=current_emp,
                           exercices=exercices,
                           current_ex=current_ex,
                           current_children=current_children,
                           emp_data=emp_data,
                           parts=parts,
                           rate=rate,
                           plafond_loc=plafond_loc,
                           plafond_sport=plafond_sport,
                           reqs_loc=reqs_loc,
                           reqs_sport=reqs_sport,
                           reqs_colo=reqs_colo,
                           cons_loc=cons_loc,
                           cons_sport=cons_sport,
                           cons_colo=cons_colo)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Identifiant ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        if not new_password:
            flash("Le nouveau mot de passe ne peut pas être vide.", "danger")
            return redirect(url_for('change_password'))
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash("Votre mot de passe a été mis à jour avec succès.", "success")
        return redirect(url_for('index'))
    return render_template('change_password.html')

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('index'))
    
    username = request.form.get('username')
    password = request.form.get('password', 'password123')
    firstname = request.form.get('firstname', '')
    lastname = request.form.get('lastname', '')
    is_admin = True if request.form.get('is_admin') else False

    if User.query.filter_by(username=username).first():
        flash("Cet identifiant existe déjà.", "warning")
        return redirect(url_for('settings_page'))

    new_user = User(
        username=username,
        password=generate_password_hash(password),
        firstname=firstname,
        lastname=lastname,
        is_admin=is_admin
    )
    db.session.add(new_user)
    db.session.commit()

    if not is_admin:
        new_emp = Employee(
            user_id=new_user.id,
            username=username,
            firstname=firstname,
            lastname=lastname
        )
        db.session.add(new_emp)
        db.session.commit()

    flash("Utilisateur ajouté avec succès.", "success")
    return redirect(url_for('settings_page'))

@app.route('/toggle_admin/<string:user_id>')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash("Action réservée à l'administrateur.", "danger")
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    if user.username == 'admin' and user.is_admin:
        flash("Impossible de retirer les droits administrateur du compte principal 'admin'.", "danger")
        return redirect(url_for('settings_page'))

    # Empêcher un admin de s'auto-retirer ses propres droits s'il est le seul (ou par sécurité)
    if user.id == current_user.id and current_user.is_admin:
        flash("Vous ne pouvez pas vous retirer vos propres droits administrateur.", "warning")
        return redirect(url_for('settings_page'))

    # Bascule du statut admin (True devient False, et inversement)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"Le rôle de l'utilisateur {user.username} a été mis à jour.", "success")
    return redirect(url_for('settings_page'))

@app.route('/employee/<string:emp_id>/exercice/add', methods=['POST'])
@login_required
def add_exercice(emp_id):
    if not can_access_employee(emp_id):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))

    year = request.form.get('year', type=int)
    if year:
        existing = Exercice.query.filter_by(employee_id=emp_id, year=year).first()
        if existing:
            flash(f"L'exercice {year} existe déjà pour ce salarié.", 'warning')
        else:
            new_ex = Exercice(employee_id=emp_id, year=year)
            db.session.add(new_ex)
            db.session.commit()
            emp_data = EmpData(exercice_id=new_ex.id, rfr=0.0, en_couple=False, parent_isole=False)
            db.session.add(emp_data)
            db.session.commit()
            flash(f"Exercice {year} créé avec succès.", 'success')
            return redirect(url_for('index', emp_id=emp_id, ex_id=new_ex.id))
    return redirect(url_for('index', emp_id=emp_id))

@app.route('/exercice/<string:ex_id>/delete')
@login_required
def delete_exercice(ex_id):
    ex = Exercice.query.get_or_404(ex_id)
    if not can_access_employee(ex.employee_id):
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('index'))

    emp_id = ex.employee_id
    db.session.delete(ex)
    db.session.commit()
    flash("L'exercice et toutes ses données ont été supprimés.", 'success')
    return redirect(url_for('index', emp_id=emp_id))

@app.route('/delete_employee/<string:emp_id>')
@login_required
def delete_employee(emp_id):
    if not current_user.is_admin:
        flash("Action réservée à l'administrateur.", "danger")
        return redirect(url_for('index'))

    user_to_delete = User.query.get_or_404(emp_id)
    if user_to_delete.username == 'admin':
        flash("Impossible de supprimer le compte administrateur principal.", "danger")
        return redirect(url_for('settings_page'))
    if user_to_delete.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
        return redirect(url_for('settings_page'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash("L'utilisateur a été supprimé avec succès.", "success")
    return redirect(url_for('settings_page'))

@app.route('/employee/<string:emp_id>/child/add', methods=['POST'])
@login_required
def add_child(emp_id):
    if not can_access_employee(emp_id):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))

    ex_id = request.args.get('ex_id', type=str)
    firstname = request.form.get('child_name')
    active_tab = request.form.get('active_tab', 'loc')

    ex = Exercice.query.filter_by(id=ex_id, employee_id=emp_id).first()
    if ex and firstname:
        child = Child(exercice_id=ex.id, firstname=firstname)
        db.session.add(child)
        db.session.commit()
        flash("Enfant ajouté avec succès.", 'success')
    return redirect(url_for('index', emp_id=emp_id, ex_id=ex_id, active_tab=active_tab))

@app.route('/child/<string:child_id>/delete')
@login_required
def delete_child(child_id):
    child = Child.query.get_or_404(child_id)
    ex = Exercice.query.get(child.exercice_id)
    
    if not ex or not can_access_employee(ex.employee_id):
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('index'))

    emp_id = ex.employee_id
    db.session.delete(child)
    db.session.commit()
    flash("Enfant supprimé.", 'success')
    return redirect(url_for('index', emp_id=emp_id, ex_id=ex.id))

@app.route('/employee/<string:emp_id>/exercice/<string:ex_id>/update-data', methods=['POST'])
@login_required
def update_emp_data(emp_id, ex_id):
    if not can_access_employee(emp_id):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))

    ex = Exercice.query.filter_by(id=ex_id, employee_id=emp_id).first_or_404()
    emp_data = EmpData.query.filter_by(exercice_id=ex.id).first()
    if not emp_data:
        emp_data = EmpData(exercice_id=ex.id)
        db.session.add(emp_data)

    emp_data.rfr = request.form.get('rfr', type=float, default=0.0)
    emp_data.en_couple = True if request.form.get('en_couple') else False
    emp_data.parent_isole = True if request.form.get('parent_isole') else False

    if emp_data.en_couple and emp_data.parent_isole:
        emp_data.parent_isole = False

    active_tab = request.form.get('active_tab', 'loc')

    db.session.commit()
    flash("Données fiscales mises à jour.", 'success')
    return redirect(url_for('index', emp_id=emp_id, ex_id=ex_id, active_tab=active_tab))

@app.route('/employee/<string:emp_id>/request/add', methods=['POST'])
@login_required
def add_request(emp_id):
    if not can_access_employee(emp_id):
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('index'))

    ex_id = request.form.get('exercice_id', type=str)
    ex = Exercice.query.filter_by(id=ex_id, employee_id=emp_id).first_or_404()

    active_tab = request.form.get('active_tab', 'loc')

    category = request.form.get('category')
    label = request.form.get('label')
    amount = request.form.get('amount', type=float, default=0.0)
    beneficiary = request.form.get('beneficiary')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # Contrôle : la date de fin doit être postérieure ou égale à la date de début
    if start_date and end_date and end_date < start_date:
        flash("La date de fin doit être postérieure ou égale à la date de début.", 'danger')
        return redirect(url_for('index', emp_id=emp_id, ex_id=ex.id, active_tab=active_tab))

    filename = None
    file = request.files.get('invoice_file')
    if file and allowed_file(file.filename):
        safe_name = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}_{safe_name}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    children = Child.query.filter_by(exercice_id=ex.id).all()
    emp_data = EmpData.query.filter_by(exercice_id=ex.id).first()

    raw_settings = {s.key: s.value for s in GlobalSettings.query.all()}
    parts = calculate_parts(emp_data, len(children))

    if category == 'sport':
        rate = float(raw_settings.get('sport_taux', 50.0))
    else:
        rate = get_subsidy_rate(emp_data.rfr if emp_data else 0.0, parts, raw_settings)

    subsidized = amount * (rate / 100.0)

    # Plafond Location : il est calculé selon le RFR, les parts fiscales
    # et le nombre d'enfants. Une nouvelle demande ne peut pas dépasser
    # le montant restant disponible sur ce plafond.
    if category == 'location':
        _, plafond_loc = get_subsidy_details(
            emp_data.rfr if emp_data else 0.0,
            parts,
            len(children),
            raw_settings
        )

        existing_reqs = Request.query.filter_by(
            exercice_id=ex.id,
            category='location'
        ).all()
        already_consumed = sum(r.amount_subsidized for r in existing_reqs)
        remaining_plafond = max(0.0, plafond_loc - already_consumed)

        # Le plafond est déjà atteint/dépassé : aucune nouvelle
        # subvention de location ne peut être enregistrée.
        if remaining_plafond <= 0.0:
            flash(
                f"Le plafond Location Familiale de {plafond_loc:.2f} € est déjà atteint ou dépassé. "
                f"Consommé : {already_consumed:.2f} €.",
                'danger'
            )
            return redirect(url_for('index', emp_id=emp_id, ex_id=ex.id, active_tab=active_tab))

        # Si la subvention calculée dépasse le reliquat, elle est limitée
        # exactement au montant encore disponible.
        subsidized = min(subsidized, remaining_plafond)

    # Plafonds Sport & Culture par bénéficiaire
    if category == 'sport':
        # 1. Déterminer le plafond autorisé pour ce bénéficiaire spécifique
        if beneficiary == 'Salarie':
            plafond_benef = float(raw_settings.get('sport_salarie', 200.0))
        elif beneficiary == 'Conjoint':
            plafond_benef = float(raw_settings.get('sport_conjoint', 100.0))
        else:
            plafond_benef = float(raw_settings.get('sport_enfant', 100.0))

        # 2. Calculer ce qui a déjà été consommé par CE bénéficiaire précis pour cet exercice
        existing_reqs = Request.query.filter_by(exercice_id=ex.id, category='sport', beneficiary=beneficiary).all()

        # 3. Vérifier le reste disponible pour ce bénéficiaire
        already_consumed = sum(r.amount_subsidized for r in existing_reqs)
        remaining_plafond = max(0.0, plafond_benef - already_consumed)

        # 4. Limiter la subvention au reste disponible
        if subsidized > remaining_plafond:
            subsidized = remaining_plafond

    new_req = Request(
        exercice_id=ex.id,
        category=category,
        label=label,
        amount_invoiced=amount,
        amount_subsidized=subsidized,
        beneficiary=beneficiary,
        start_date=start_date,
        end_date=end_date,
        invoice_file=filename
    )
    db.session.add(new_req)
    db.session.commit()

    flash("Demande de subvention enregistrée avec succès.", 'success')
    return redirect(url_for('index', emp_id=emp_id, ex_id=ex.id, active_tab=active_tab))

@app.route('/request/<string:req_id>/delete')
@login_required
def delete_request(req_id):
    req = Request.query.get_or_404(req_id)
    ex = Exercice.query.get(req.exercice_id)

    if not ex or not can_access_employee(ex.employee_id):
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('index'))

    emp_id = ex.employee_id
    if req.invoice_file:
        path = os.path.join(app.config['UPLOAD_FOLDER'], req.invoice_file)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(req)
    db.session.commit()
    flash("Demande supprimée.", 'success')
    return redirect(url_for('index', emp_id=emp_id, ex_id=ex.id))

@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    req = Request.query.filter_by(invoice_file=filename).first_or_404()
    ex = Exercice.query.get(req.exercice_id)

    if not ex or not can_access_employee(ex.employee_id):
        flash("Accès non autorisé au fichier.", "danger")
        return redirect(url_for('index'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    if not current_user.is_admin:
        flash("Accès réservé à l'administrateur.", 'danger')
        return redirect(url_for('index'))

    users = User.query.all()

    if request.method == 'POST':
        for key, value in request.form.items():
            if key != 'csrf_token':
                setting = GlobalSettings.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    db.session.add(GlobalSettings(key=key, value=value))
        db.session.commit()
        flash("Paramètres mis à jour avec succès.", "success")
        return redirect(url_for('settings_page'))

    raw_settings = GlobalSettings.query.all()
    settings = {s.key: s.value for s in raw_settings}

    # QF (Seuils de base 1 part)
    if 'seuil_1' not in settings: settings['seuil_1'] = '10849.00'
    if 'seuil_2' not in settings: settings['seuil_2'] = '14291.00'
    if 'seuil_3' not in settings: settings['seuil_3'] = '16987.00'
    if 'seuil_4' not in settings: settings['seuil_4'] = '20351.00'
    if 'seuil_5' not in settings: settings['seuil_5'] = '23754.00'

    # Plafonds de base par tranche
    if 'plafond_t1' not in settings: settings['plafond_t1'] = '750.00'
    if 'plafond_t2' not in settings: settings['plafond_t2'] = '700.00'
    if 'plafond_t3' not in settings: settings['plafond_t3'] = '650.00'
    if 'plafond_t4' not in settings: settings['plafond_t4'] = '500.00'
    if 'plafond_t5' not in settings: settings['plafond_t5'] = '350.00'
    if 'plafond_t6' not in settings: settings['plafond_t6'] = '300.00'

    # Majoration par enfant et plafond sport
    if 'majoration_enfant' not in settings: settings['majoration_enfant'] = '40.00'
    if 'plafond_sport' not in settings: settings['plafond_sport'] = '200.00'

    if 'sport_taux' not in settings: settings['sport_taux'] = '50.0'
    if 'sport_salarie' not in settings: settings['sport_salarie'] = '200.0'
    if 'sport_conjoint' not in settings: settings['sport_conjoint'] = '100.0'
    if 'sport_enfant' not in settings: settings['sport_enfant'] = '100.0'

    return render_template('settings.html', users=users, settings=settings)

# ================= INITIALISATION =================
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin123'),
                firstname='Administrateur',
                lastname='CE',
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)