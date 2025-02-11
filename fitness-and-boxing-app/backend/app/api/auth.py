from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    # Extract data from request
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'])
    
    # Print the hashed password for debugging
    print("Hashed during registration:", hashed_password)
    
    # Create new user model instance
    new_user = User(username=data['username'], email=data['email'], password_hash=hashed_password)
    
    # Add to the database session and commit
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User created successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    # Debug: Directly hash the incoming password for comparison
    attempted_hash = generate_password_hash(data['password'])
    print("Attempted hash for provided password:", attempted_hash)
    print("Stored hash:", user.password_hash)

    if user and check_password_hash(user.password_hash, data['password']):
        # Placeholder for token generation
        token = "dummy_token_for_" + user.username
        return jsonify({"message": "Login successful", "token": token}), 200
    else:
        print("Password verification failed.")
        return jsonify({"error": "Invalid username or password"}), 401
