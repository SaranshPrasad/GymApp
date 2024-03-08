from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sahgdyevdjvwy'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = 'static\\uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")


db = SQLAlchemy(app)

# Define GymMember model
class GymMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    admission_date = db.Column(db.Date, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    last_paid = db.Column(db.Date, nullable=False)
    photo_path = db.Column(db.String(255))

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
# Routes
@app.route('/')
def index():
    is_logged_in = True
    if 'admin_logged_in' not in session:
        is_logged_in = False
        return render_template("index.html", admin=is_logged_in)
    return render_template("index.html", admin=is_logged_in)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'admin@example.com' and password == '123':
            session['admin_logged_in'] = True
            flash('You have successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check your email and password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    members = GymMember.query.order_by(GymMember.admission_date).all()
    nearest_due_date = db.session.query(func.min(GymMember.due_date)).filter(GymMember.due_date >= datetime.now().date()).scalar()   
    today_date = datetime.now().date()
    search_query = request.args.get('search')
    if search_query:
        members = GymMember.query.filter(GymMember.username.ilike(f'%{search_query}%')).all()
    else:
        members = GymMember.query.all()
    
    
    return render_template('dashboard.html', members=members, nearest_due_date=nearest_due_date, today=today_date)

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        admission_date = datetime.strptime(request.form['admission_date'], '%Y-%m-%d').date()
        amount = float(request.form['amount'])
        last_paid = datetime.now().date()
        if request.form['due_date']:
            due_date = request.form['due_date']
        else:
            due_date = admission_date + timedelta(days=30)

        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)   

        new_member = GymMember(username=username, email=email, phone_number=phone, admission_date=admission_date,
                               amount_paid=amount,  due_date=due_date, last_paid=last_paid, photo_path=file_path)
        db.session.add(new_member)
        db.session.commit()
        
        flash('Member added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_member.html')

@app.route('/notifications')
def notifications():
    
    due_members = GymMember.query.filter(GymMember.due_date <= datetime.now().date()).all()
    return render_template('notification.html', due_members=due_members)


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/update_due_date/<int:member_id>', methods=['POST'])
def update_due_date(member_id):
    member = GymMember.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    payment_amount = float(request.form['payment_amount'])
    if payment_amount >= member.amount_paid:
        new_due_date = member.due_date + timedelta(days=30)
        member.due_date = new_due_date
        member.amount_paid = payment_amount 
        member.last_paid = datetime.now().date()
        db.session.commit()
        flash('Paid amount updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Paid amount is less than previous amount', 'danger')
        return redirect(url_for('dashboard'))
    
@app.route('/member/photo/<path:filename>')
def get_member_photo(filename):
    # Serve the uploaded image from the upload folder
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
 
@app.route('/delete_member/<int:user_id>', methods=['POST'])
def delete_member(user_id):
    member = GymMember.query.get_or_404(user_id)
    db.session.delete(member)
    db.session.commit()
    flash('Member deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/view_member/<int:user_id>', methods=["GET", "POST"])
def view_member(user_id):
    member = GymMember.query.get(user_id)
    photo = member.photo_path
    return render_template("member.html", member=member, photo=photo)


