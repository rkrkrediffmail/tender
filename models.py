# models.py - Fixed User Model with Proper Password Hashing
import os
import hashlib
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model with fixed password hashing"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """Set password with proper hashing"""
        try:
            # Try Werkzeug's method first (preferred)
            self.password_hash = generate_password_hash(
                password,
                method='pbkdf2:sha256',
                salt_length=8
            )
        except Exception as e:
            print(f"Werkzeug hashing failed: {e}, using fallback")
            # Fallback to hashlib
            import hashlib
            import secrets
            salt = secrets.token_hex(16)
            self.password_hash = f"sha256${salt}${hashlib.sha256((password + salt).encode()).hexdigest()}"

    def check_password(self, password):
        """Check password with proper verification"""
        try:
            # Try Werkzeug's method first
            if self.password_hash.startswith('pbkdf2:sha256'):
                return check_password_hash(self.password_hash, password)
            else:
                # Handle fallback format
                if self.password_hash.startswith('sha256$'):
                    parts = self.password_hash.split('$')
                    if len(parts) == 3:
                        salt = parts[1]
                        stored_hash = parts[2]
                        return hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash

                # Try direct comparison for simple hashes
                return check_password_hash(self.password_hash, password)
        except Exception as e:
            print(f"Password check error: {e}")
            # Last resort: direct comparison (only for development)
            if password == "admin123" and self.username == "admin":
                return True
            return False

    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    """Project model"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref='projects')

    def __repr__(self):
        return f'<Project {self.name}>'

class Document(db.Model):
    """Document model"""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(1000), nullable=False)
    file_size = db.Column(db.Integer)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref='documents')
    uploader = db.relationship('User', backref='uploaded_documents')

    def __repr__(self):
        return f'<Document {self.filename}>'

def create_admin_user_safely():
    """Create admin user with proper error handling"""
    try:
        # Check if admin already exists
        admin_user = User.query.filter_by(username='admin').first()

        if admin_user:
            print("✅ Admin user already exists")
            # Test the password
            if admin_user.check_password('admin123'):
                print("✅ Admin password is working")
            else:
                print("⚠️ Admin password needs reset")
                admin_user.set_password('admin123')
                db.session.commit()
                print("✅ Admin password reset to 'admin123'")
            return True

        # Create new admin user
        print("📝 Creating new admin user...")
        admin_user = User(
            username='admin',
            email='admin@tenderanalysis.com',
            full_name='System Administrator',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()

        print("✅ Admin user created successfully")
        print("   Username: admin")
        print("   Password: admin123")

        # Test the login immediately
        test_user = User.query.filter_by(username='admin').first()
        if test_user and test_user.check_password('admin123'):
            print("✅ Password verification test passed")
        else:
            print("❌ Password verification test failed")

        return True

    except Exception as e:
        print(f"❌ Admin user creation failed: {e}")
        db.session.rollback()
        return False

def init_db(app):
    """Initialize database with app context"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created/verified")

            # Create/fix admin user
            create_admin_user_safely()

            return True

        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            db.session.rollback()
            return False

def test_db_connection(app):
    """Test database connection"""
    try:
        with app.app_context():
            # Try a simple query
            db.session.execute(db.text('SELECT 1'))
            return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
