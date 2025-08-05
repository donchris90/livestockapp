import os
import uuid
import requests
from decimal import Decimal
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from app.forms import OfferForm,OfferAmountForm,CreateOrderForm
from sqlalchemy import Enum
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, abort,session
)
from flask_login import login_required, current_user
from app.utils.paystack import transfer_funds_to_seller,create_and_transfer_to_recipient

from app.utils.paystack import initialize_transaction

from app.models import Product, EscrowPayment, Order,User,Wallet,PlatformWallet,ProfitHistory,PaymentStatus,OrderStatus,StatusEnum
from app.extensions import db
from app.forms import EscrowPaymentForm
from app.utils.paystack_utils import verify_paystack_transaction
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
from app.utils.paystack import verify_paystack_payment

escrow_bp = Blueprint('escrow', __name__, url_prefix='/escrow')

import uuid

reference = str(uuid.uuid4())
def generate_unique_reference():
    return str(uuid.uuid4()).replace('-', '')[:15]
# routes.py
def get_admin_account():
    return User.query.filter_by(role="admin").first()




@escrow_bp.route("/verify-payment/<int:escrow_id>")
@login_required
def verify_payment(escrow_id):
    reference = request.args.get("reference")
    if not reference:
        flash("Payment reference is missing.", "danger")
        return redirect(url_for("escrow.my_escrows"))

    headers = {
        "Authorization": f"Bearer {current_app.config['PAYSTACK_SECRET_KEY']}"
    }

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(verify_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data["status"] and data["data"]["status"] == "success":
            escrow = EscrowPayment.query.get_or_404(escrow_id)
            product = Product.query.get_or_404(escrow.product_id)

            # ✅ Update escrow as paid
            escrow.status = "paid"
            escrow.is_paid = True
            escrow.payment_reference = reference

            # ✅ Log platform fee (5%) as profit
            platform_fee = product.price * Decimal("0.05")

            log = ProfitHistory(
                user_id=current_user.id,
                product_id=product.id,
                source_type='escrow',
                description=f"Escrow Fee on {product.title}",
                amount=platform_fee,
                reference=reference,
                status="success"
            )
            db.session.add(log)

            # ✅ Update platform wallet
            wallet = PlatformWallet.query.get(1) or PlatformWallet(id=1)
            wallet.balance = Decimal(wallet.balance) + platform_fee
            wallet.total_earned = Decimal(wallet.total_earned) + platform_fee

            db.session.add(wallet)

            db.session.commit()
            flash("✅ Payment successful and verified!", "success")
        else:
            flash("❌ Payment verification failed.", "danger")
    else:
        flash("❌ Unable to verify payment. Please try again.", "danger")

    return redirect(url_for("escrow.my_escrows"))


@escrow_bp.route("/payment/callback")
def payment_callback():
    reference = request.args.get("reference")
    print("Callback hit! Reference:", reference)

    if not reference:
        flash("Invalid payment reference.", "danger")
        return redirect(url_for("seller_dashboard.my_escrows"))

    payment_data = verify_paystack_payment(reference)
    print("Paystack Response:", payment_data)

    if not payment_data or not payment_data.get("status"):
        flash("Payment verification failed. Please try again.", "danger")
        return redirect(url_for("seller_dashboard.my_escrows"))

    status = payment_data["data"]["status"]

    if status == "success":
        escrow = EscrowPayment.query.filter_by(payment_reference=reference).first()
        if escrow:
            escrow.status = "paid"
            escrow.paid_at = datetime.utcnow()
            db.session.commit()
            flash("Payment successful!", "success")
        else:
            flash("No matching escrow record found.", "warning")
    else:
        flash("Payment was not successful.", "danger")

    return redirect(url_for("seller_dashboard.my_escrows"))

@escrow_bp.route('/escrow-wallet')
@login_required
def escrow_wallet():
    return render_template("escrow_wallet.html", user=current_user)

@escrow_bp.route("/escrow-dashboard")
@login_required
def escrow_dashboard():
    total_balance = db.session.query(func.sum(EscrowPayment.amount)).filter_by(
        buyer_id=current_user.id,
        is_paid=True
    ).scalar() or 0.0

    return render_template("seller_dashboard.my_escrows", total_balance=total_balance)


@escrow_bp.route('/pay-now/<int:product_id>', methods=["GET", "POST"])

@login_required
def pay_now(product_id):
    escrow = EscrowPayment.query.filter_by(product_id=product_id, buyer_id=current_user.id).first()

    if not escrow:
        flash("No escrow record found.", "danger")
        return redirect(url_for('seller_dashboard.product_detail', product_id=product_id))

    escrow.is_paid = True
    escrow.payment_reference = request.form.get("reference")  # if using Paystack or similar
    escrow.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Payment successful. You can now confirm order after delivery.", "success")
    return redirect(url_for('seller_dashboard.confirm_order', escrow_id=escrow.id))




from uuid import uuid4

@escrow_bp.route("/submit-offer/<int:product_id>", methods=["GET", "POST"])
@login_required
def escrow_offer(product_id):
    product = Product.query.get_or_404(product_id)
    seller = User.query.get_or_404(product.user_id)

    if request.method == "POST":
        offer_amount_raw = request.form.get("offer_amount")

        if not offer_amount_raw:
            flash("Offer amount is required.", "danger")
            return redirect(request.url)

        try:
            base_amount = float(offer_amount_raw)
        except ValueError:
            flash("Invalid offer amount.", "danger")
            return redirect(request.url)

        # ✅ Calculate fees
        escrow_fee = round(base_amount * 0.03, 2)
        total_amount = round(base_amount + escrow_fee, 2)
        form = OfferForm()

        offer_amount = form.offer_amount.data or product.price

        # ✅ Generate a unique UUID reference
        reference = str(uuid4())

        # ✅ Check if an escrow already exists for this buyer & product
        existing_escrow = EscrowPayment.query.filter_by(
            buyer_id=current_user.id, product_id=product.id
        ).first()

        if existing_escrow:
            flash("You have already submitted an offer for this product.", "warning")
            return redirect(url_for("escrow.my_escrows", product_id=product.id))

        # ✅ Save to EscrowPayment
        new_payment = EscrowPayment(
            product_id=product.id,

            buyer_id=current_user.id,
            seller_id=seller.id,
            base_amount=base_amount,
            escrow_fee=escrow_fee,
            total_amount=total_amount,
            amount=total_amount,  # optional legacy field
            offer_amount=offer_amount,
            status='pending',
            is_paid=False,
            is_read=False,
            created_at=datetime.utcnow(),
            reference=reference,
            buyer_name=f"{current_user.first_name} {current_user.last_name}",
            seller_name=f"{seller.first_name} {seller.last_name}"
        )

        db.session.add(new_payment)
        db.session.commit()

        flash(f"Offer of ₦{base_amount:,} + ₦{escrow_fee:,} fee (₦{total_amount:,} total) submitted successfully!", "success")
        return redirect(url_for("escrow.my_escrows", product_id=product.id))

    return render_template("escrow/offer_form.html", product_id=product_id)



@escrow_bp.route('/my-escrows')
@login_required
def my_escrows():
    user = current_user

    # Escrows where the user is buyer
    buyer_escrows = EscrowPayment.query.filter_by(buyer_id=user.id).order_by(EscrowPayment.created_at.desc()).all()

    # Escrows where the user is seller
    seller_escrows = EscrowPayment.query.filter_by(seller_id=user.id).order_by(EscrowPayment.created_at.desc()).all()

    # Count unread escrows (for bell notification)
    escrow_unread_count = EscrowPayment.query.filter(
        ((EscrowPayment.buyer_id == user.id) | (EscrowPayment.seller_id == user.id)) &
        (EscrowPayment.is_read == False)
    ).count()

    # ✅ Get Paystack public key from config
    paystack_public_key = current_app.config.get("PAYSTACK_PUBLIC_KEY")

    return render_template(
        'escrow/view_escrow.html',
        buyer_escrows=buyer_escrows,
        seller_escrows=seller_escrows,
        escrow_unread_count=escrow_unread_count,
        paystack_public_key=current_app.config.get("PAYSTACK_PUBLIC_KEY") # ✅ add to template
    )

# Mark Escrow as Complete
@escrow_bp.route("/mark-complete/<int:escrow_id>", methods=["POST"])
@login_required
def mark_complete(escrow_id):
    escrow = EscrowPayment.query.get_or_404(escrow_id)

    is_buyer = escrow.buyer_id == current_user.id
    is_admin = current_user.role == 'admin'

    # 🛡 Access control
    if not (is_buyer or is_admin):
        flash("You are not authorized to complete this transaction.", "danger")
        return redirect(url_for("seller_dashboard.my_dashboard"))

    # ⛔ Prevent multiple markings
    if escrow.status != "paid":
        flash("You can only mark this transaction complete after payment has been made.", "warning")
        return redirect(url_for("seller_dashboard.my_dashboard"))

    # ✅ Get admin user and wallet
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        flash("Admin user not found.", "danger")
        return redirect(url_for("seller_dashboard.my_dashboard"))

    admin_wallet = Wallet.query.filter_by(user_id=admin_user.id).first()
    if not admin_wallet:
        flash("Admin wallet not found.", "danger")
        return redirect(url_for("seller_dashboard.my_dashboard"))

    # ✅ Get seller's wallet
    seller_wallet = Wallet.query.filter_by(user_id=escrow.seller_id).first()
    if not seller_wallet:
        flash("Seller wallet not found.", "danger")
        return redirect(url_for("seller_dashboard.my_dashboard"))

    # 💵 Split funds: send amount_offer to seller, fee to admin
    amount_offer = escrow.offer_amount
    escrow_fee = escrow.escrow_fee or 0  # default to 0 if None

    seller_wallet.balance += amount_offer
    admin_wallet.balance += escrow_fee

    # 🔁 Update escrow
    escrow.status = "completed"
    escrow.buyer_marked_complete = True
    escrow.completed_at = datetime.utcnow()
    escrow.marked_by_admin = is_admin
    escrow.marked_by_user_id = current_user.id

    db.session.commit()

    # 📢 Optional: Send notifications

    if is_admin:
        flash("You have marked the transaction as complete on behalf of the buyer.", "success")
    else:
        flash("Transaction marked as complete!", "success")

    return redirect(url_for("seller_dashboard.my_dashboard"))


@escrow_bp.route("/mark-delivered/<int:escrow_id>", methods=["POST"])
@login_required
def mark_delivered(escrow_id):
    escrow = EscrowPayment.query.get_or_404(escrow_id)

    if escrow.status == 'released':
        flash("Order already completed.", "warning")
        return redirect(url_for("seller_dashboard.my_escrows"))

    escrow.status = 'delivered_by_buyer'
    escrow.delivered_at = datetime.utcnow()
    db.session.commit()
    flash("You marked the order as delivered. Admin will release payment shortly.", "success")
    return redirect(url_for("seller_dashboard.my_escrows"))


# routes/order.py (or wherever appropriate)
@escrow_bp.route("/create-order/<int:product_id>", methods=["GET", "POST"])
@login_required
def create_order(product_id):
    form = CreateOrderForm()
    product = Product.query.get_or_404(product_id)

    if form.validate_on_submit():
        quantity = form.quantity.data
        agreed_price = product.price
        total_amount = agreed_price * quantity

        order = Order(
            buyer_id=current_user.id,
            seller_id=product.user_id,
            product_id=product.id,
            quantity=quantity,
            agreed_price=form.agreed_price.data,
            total_amount=total_amount,
            status=StatusEnum.pending.value,  # inserts 'pending'
            payment_status=PaymentStatus.pending.value,  # inserts 'pending'
            order_status = OrderStatus.INITIATED.value,

        )

        db.session.add(order)
        db.session.commit()
        flash("Order created successfully!", "success")
        return redirect(url_for("seller_dashboard.my_orders"))

    return render_template("create_order.html", form=form, product=product)
@escrow_bp.route('/escrow/<int:order_id>', methods=['GET'])
@login_required
def view_escrow(order_id):
    order = Order.query.get(order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('seller_dashboard.my_orders'))

    escrow = EscrowPayment.query.filter_by(order_id=order.id).first()

    if not escrow:
        flash("Escrow record not found for this order.", "danger")
        return redirect(url_for('seller_dashboard.my_orders'))

    product = Product.query.get(order.product_id)

    return render_template(
        'escrow/view_escrow.html',
        escrow=escrow,
        order=order,
        product=product
    )

