# app/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import User,Wallet
from app.extensions import db


from app.forms import LoginForm
from app.utils.email_utils import send_email  # ✅ Import this at the top



auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ------------------------------
# Login Route
# ------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('✅ Logged in successfully.', 'success')
            return redirect(url_for('main.home'))  # or your dashboard route
        else:
            flash('❌ Invalid credentials. Please try again.', 'danger')
            return redirect(url_for('auth.login'))  # stay on login page

    return render_template("login.html", form=form)



# ------------------------------
# Registration Route
# ------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        state = request.form.get('state')
        city = request.form.get('city')
        street = request.form.get('street')
        phone = request.form.get('phone')
        password = request.form.get('password')


        if not all([role, email, first_name, last_name, state, city, street, phone, password]):
            flash("All fields are required.", "warning")
            return redirect(url_for('auth.register'))

        existing_user = User.query.filter((User.email == email) | (User.phone == phone)).first()
        if existing_user:
            flash("A user with this email or phone already exists.", "danger")
            return redirect(url_for('auth.register'))

        new_user = User(
            role=role,
            email=email,
            first_name=first_name,
            last_name=last_name,
            state=state,
            city=city,
            street=street,
            phone=phone
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # ✅ Create wallet after user is saved
        wallet = Wallet(user_id=new_user.id, balance=0)
        db.session.add(wallet)
        db.session.commit()

        text_body = f"""Hi {new_user.first_name},

        Welcome to the Livestock Farm App!

        You can now explore products, book agents, chat with providers, and more.

        Visit: https://your-app-url.com

        - Livestock Farm App Team
        """

        html_body = render_template('email/welcome_email.html', name=new_user.first_name)

        send_email(
            to=new_user.email,
            subject="🎉 Welcome to Livestock Farm App!",
            body=text_body,
            html=html_body
        )

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html')

# ------------------------------
# Logout Route
# ------------------------------
@auth_bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        current_user.is_online = False
        db.session.commit()
    logout_user()
    return redirect(url_for('auth.login'))
