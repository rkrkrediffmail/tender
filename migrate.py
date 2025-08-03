from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade
import os

def setup_migrations():
    """Setup database migrations for the enhanced schema"""

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/tender_analysis')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate_instance = Migrate(app, db)

    with app.app_context():
        # Initialize migration repository if it doesn't exist
        if not os.path.exists('migrations'):
            init()

        # Create migration for new schema
        migrate(message='Add multi-document RFP support')

        # Apply migrations
        upgrade()
