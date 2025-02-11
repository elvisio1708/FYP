from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, ForeignKey, Integer, String
from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    profile = db.relationship('UserProfile', backref='user', uselist=False)
    training_plans = db.relationship('TrainingPlan', backref='user')
    progress = db.relationship('UserProgress', backref='user')
    feedback = db.relationship('Feedback', backref='user')

class UserProfile(db.Model):
    __tablename__ = 'UserProfiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    fitness_level = db.Column(db.String(50))
    experience_level = db.Column(db.String(50))
    goals = db.Column(db.Text)

class TrainingPlan(db.Model):
    __tablename__ = 'TrainingPlans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(50))

    training_sessions = db.relationship('TrainingSession', backref='training_plan')

class Exercise(db.Model):
    __tablename__ = 'Exercises'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    difficulty_level = db.Column(db.String(50))
    type = db.Column(db.String(50))
    video_url = db.Column(db.String(255))

class TrainingSession(db.Model):
    __tablename__ = 'TrainingSessions'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('TrainingPlans.id'))
    date = db.Column(db.DateTime)
    duration = db.Column(db.Integer)
    feedback = db.Column(db.Text)

    session_exercises = db.relationship('SessionExercise', backref='training_session')

class SessionExercise(db.Model):
    __tablename__ = 'SessionExercises'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('TrainingSessions.id'))
    exercise_id = db.Column(db.Integer, db.ForeignKey('Exercises.id'))
    reps = db.Column(db.Integer)
    sets = db.Column(db.Integer)
    notes = db.Column(db.Text)

class UserProgress(db.Model):
    __tablename__ = 'UserProgress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.DateTime)
    metric = db.Column(db.String(100))
    value = db.Column(db.Float)

class Feedback(db.Model):
    __tablename__ = 'Feedback'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.DateTime)
    content = db.Column(db.Text)
    response = db.Column(db.Text)
