from flask import render_template, url_for, flash, redirect, request, jsonify, make_response
from app import app, db
from app.forms import RegistrationForm, LoginForm
from app.models import User
from app.models import TrainingPlan
from flask_login import login_user, current_user, logout_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data['username'] or not data['password'] or not data['email']:
        return jsonify({'message': 'Missing data'}), 400

    # Check if user already exists
    if User.query.filter_by(username=data['username']).first() is not None:
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.query.filter_by(username=data['username']).first()

        if user and user.verify_password(data['password']):
            login_user(user)
            return redirect(url_for('userDashboard'))
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        # Log the error for debugging
        print(f"Unexpected error during login: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

    # Fallback return statement (shouldn't be reached in theory, but good practice to include)
    return jsonify({'error': 'Unhandled request condition'}), 500

@app.route('/userDashboard')
def dashboard():
    # Assuming 'current_user' is used to access the logged-in user information
    if current_user.is_authenticated:
        return render_template('userDashboard.html')  # Or your logic for displaying the dashboard
    else:
        flash('Please log in to access this page.')
        return redirect(url_for('login'))  # Redirect to login page if not logged in

@app.route('/api/training-plan', methods=['POST'])
def create_training_plan():
    if not current_user.is_authenticated:
        return jsonify({"error": "User not authenticated"}), 401
    
    data = request.get_json()
    new_plan = TrainingPlan(
        user_id=current_user.id,
        age=data.get('age'),
        weight=data.get('weight'),
        fitness_level=data.get('fitness_level'),
        experience_level=data.get('experience_level'),
        goals=data.get('goals'),
        # Add any other fields you need
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify({"message": "Training plan created successfully", "plan": new_plan.to_dict()}), 201