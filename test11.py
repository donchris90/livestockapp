from app import db
from app.models import User, Wallet
from decimal import Decimal

# Find the admin user
admin = User.query.filter_by(role='admin').first()

# Check if wallet already exists
existing_wallet = Wallet.query.filter_by(user_id=admin.id).first()
if not existing_wallet:
    wallet = Wallet(user_id=admin.id, balance=Decimal('0.00'))
    db.session.add(wallet)
    db.session.commit()
    print("Admin wallet created successfully.")
else:
    print("Admin wallet already exists.")
