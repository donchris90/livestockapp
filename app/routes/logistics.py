from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db,  User
from flask_login import login_required, current_user

logistics_bp = Blueprint('logistics', __name__)

@logistics_bp.route('/dashboard')
@login_required
def logistics_dashboard():
    return render_template('logistics/dashboard.html')


# Register a logistics provider
@logistics_bp.route('/register', methods=['POST'])
@jwt_required()
def register_logistics_provider():
    current_user = get_jwt_identity()
    user_id = current_user['user_id']
    role = current_user['role']

    if role != 'logistics':
        return jsonify({"message": "Only users with 'logistics' role can register as providers."}), 403

    data = request.get_json()
    company_name = data.get('company_name')
    phone = data.get('phone')
    location = data.get('location')

    if not company_name or not location:
        return jsonify({"message": "Company name and location are required."}), 400

    provider = LogisticsProvider(
        user_id=user_id,
        company_name=company_name,
        phone=phone,
        location=location
    )
    db.session.add(provider)
    db.session.commit()

    return jsonify({"message": "Logistics provider registered successfully."}), 201

# Search logistics providers by location
@logistics_bp.route('/search', methods=['GET'])
def search_logistics():
    location = request.args.get('location')
    if not location:
        return jsonify({"message": "Location query is required."}), 400

    providers = LogisticsProvider.query.filter_by(location=location).all()
    results = []
    for p in providers:
        user = User.query.get(p.user_id)
        results.append({
            "company_name": p.company_name,
            "phone": p.phone,
            "location": p.location,
            "contact_person": user.username if user else "Unknown"
        })

    return jsonify(results), 200
