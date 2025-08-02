"""Azure-optimized Flask application initialization"""
import os
import logging
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_azure_app():
    """Create Flask app optimized for Azure App Service"""

    app = Flask(__name__)

    # Azure-specific configuration
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(32)),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_size": 20,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "max_overflow": 40,
            "connect_args": {"sslmode": "require"} if "postgres" in os.environ.get('DATABASE_URL', '') else {}
        },
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', '/tmp/uploads'),
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,  # 100MB
        AZURE_STORAGE_CONNECTION_STRING=os.environ.get('AZURE_STORAGE_CONNECTION_STRING'),
        AZURE_CONTAINER_NAME=os.environ.get('AZURE_CONTAINER_NAME', 'documents'),
        ANTHROPIC_API_KEY=os.environ.get('ANTHROPIC_API_KEY'),
        OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY'),
        REDIS_URL=os.environ.get('REDIS_URL'),
    )

    # Configure logging for Azure
    if not app.debug and os.environ.get('WEBSITE_HOSTNAME'):
        # Running in Azure App Service
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        app.logger.info('Tender Analysis System starting on Azure')

    # Initialize database
    try:
        from models import db
        db.init_app(app)

        # Initialize Flask-Migrate
        migrate = Migrate(app, db)

        with app.app_context():
            db.create_all()
            app.logger.info('Database tables created/verified')

    except Exception as e:
        app.logger.error(f'Database initialization failed: {str(e)}')

    # Register health check routes
    from health_check import register_health_routes
    register_health_routes(app)

    # Import and register main application routes
    try:
        from app import register_routes
        register_routes(app)
        app.logger.info('Application routes registered')
    except ImportError as e:
        app.logger.warning(f'Could not import main app routes: {str(e)}')
        # Create a basic route as fallback
        @app.route('/')
        def index():
            return {'message': 'Tender Analysis System - Setup in Progress'}, 200

    return app

# Create the app instance
app = create_azure_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
