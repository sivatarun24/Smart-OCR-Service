import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecret')

    # --- Initialize extensions ---
    CORS(app)
    db.init_app(app)
    bcrypt.init_app(app)

    # Import models before init migrate
    from . import models
    migrate.init_app(app, db)

    # Register routes
    from .routes import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        db.drop_all()
        db.create_all()
    return app