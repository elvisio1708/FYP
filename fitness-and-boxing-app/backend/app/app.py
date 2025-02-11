from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.models import User  # Make sure you're importing User correctly

# Initialize Flask extensions, but without any specific app
from .extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize Flask extensions with the app instance
    db.init_app(app)
    login_manager.init_app(app)

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register Blueprints
    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api')

    return app
