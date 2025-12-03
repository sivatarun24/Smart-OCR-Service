import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_login import LoginManager

load_dotenv()
logger = logging.getLogger(__name__)

db = SQLAlchemy(session_options={"expire_on_commit": False})
bcrypt = Bcrypt()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app.config['SQLALCHEMY_ECHO'] = True
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecret')

    # --- Initialize extensions ---
    CORS(app)
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    # login_manager.login_view = 'api.login'

    # Import models before init migrate
    from . import models
    migrate.init_app(app, db)

    # Register routes
    from .routes import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        logger.info("Creating database tables if they do not exist...")
        # db.drop_all()
        db.create_all()
    return app