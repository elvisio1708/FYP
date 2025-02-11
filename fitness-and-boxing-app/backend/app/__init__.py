from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from .extensions import db, login_manager
def create_app():
    # Initialize the Flask application
    app = Flask(__name__)

    # Application configuration settings
    app.config.from_object('config.Config')

    # Initialize Flask extensions with the app instance
    db.init_app(app)
    login_manager.init_app(app)

    # Import and register Blueprints
    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api')

    CORS(app)
    return app
