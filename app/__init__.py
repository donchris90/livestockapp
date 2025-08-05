from flask import Flask
from flask_login import current_user
from flask.cli import with_appcontext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import click

from app.extensions import db, login_manager, socketio, migrate, mail
from app.models import User, Product
from app.commands import register_commands
from app.context_processors import init_context_processors
from app.chat.socket_events import register_chat_events
from app.tasks.renewals import process_auto_renewals
from flask_apscheduler import APScheduler
from flask_wtf import CSRFProtect

load_dotenv()
csrf = CSRFProtect()
scheduler = APScheduler()

# ✅ Promotion Expiry Task (single clean version)
def expire_promotions():
    now = datetime.utcnow()
    products = Product.query.all()
    for product in products:
        if product.is_featured and product.featured_expiry and product.featured_expiry < now:
            product.is_featured = False
        if product.is_boosted and product.boosted_expiry and product.boosted_expiry < now:
            product.is_boosted = False
        if product.is_top and product.top_expiry and product.top_expiry < now:
            product.is_top = False
    db.session.commit()
    print("✅ Promotions expired.")

# ✅ Promotion Payment Handler
def handle_successful_promotion_payment(promotion):
    product = Product.query.get(promotion.product_id)
    if not product:
        return

    product.is_featured = product.is_boosted = product.is_top = False

    if promotion.promo_type == "featured":
        product.is_featured = True
    elif promotion.promo_type == "boosted":
        product.is_boosted = True
    elif promotion.promo_type == "top":
        product.is_top = True

    product.promotion_expiry = datetime.utcnow() + timedelta(days=promotion.days)
    db.session.commit()

# ✅ App Factory
def create_app():
    app = Flask(__name__)

    # ✅ App Configs
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:Happen123!@localhost:5432/livestockdb')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['INSPECTION_UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads/inspection_photos')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ✅ Mail Config
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME'),
    )

    # ✅ Paystack Config
    app.config['PAYSTACK_SECRET_KEY'] = os.getenv('PAYSTACK_SECRET_KEY')
    app.config['PAYSTACK_PUBLIC_KEY'] = os.getenv('PAYSTACK_PUBLIC_KEY')

    # ✅ Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)

    # ✅ Login Setup
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = 'auth.login'

    # ✅ Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.chat.routes import chat_bp
    from app.seller_dashboard.routes import seller_dashboard_bp
    from app.agents.routes import agents_bp
    from app.routes.search import search_bp
    from app.routes.admin import admin_bp
    from app.routes.escrow import escrow_bp
    from app.routes.subscription import subscription_bp
    from app.paystack_webhook import paystack_webhook_bp
    from app.routes.payout import payout_bp
    from app.routes.wallet import wallet_bp
    from app.routes.promotion import promotion_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(seller_dashboard_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(escrow_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(paystack_webhook_bp)
    app.register_blueprint(payout_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(promotion_bp)

    # ✅ Context Processors & Socket Events
    init_context_processors(app)
    register_chat_events(socketio)

    # ✅ Custom CLI Command for Auto-Renew
    @click.command('auto-renew-subscriptions')
    @with_appcontext
    def auto_renew_command():
        process_auto_renewals()
    app.cli.add_command(auto_renew_command)

    # ✅ Custom Commands
    register_commands(app)

    # ✅ User Last Seen Middleware
    @app.before_request
    def update_last_seen():
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            current_user.is_online = True
            db.session.commit()

    # ✅ Scheduler Setup
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(id='expire_promotions', func=expire_promotions, trigger='interval', minutes=10)

    # ✅ (Optional) Create tables if not using Flask-Migrate
    with app.app_context():
        db.create_all()

    return app
