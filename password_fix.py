#!/usr/bin/env python3
"""
Password fix script - Fix the digestmod error
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def fix_admin_password():
    """Fix admin user password with proper hashing"""
    print("🔧 Fixing admin user password...")

    try:
        from main import app
        from models import db, User

        with app.app_context():
            # Find admin user
            admin_user = User.query.filter_by(username='admin').first()

            if not admin_user:
                print("❌ Admin user not found, creating new one...")
                admin_user = User(
                    username='admin',
                    email='admin@tenderanalysis.com',
                    full_name='System Administrator',
                    role='admin'
                )
                db.session.add(admin_user)

            # Reset password with proper method
            print("🔑 Setting password with fixed hashing...")

            # Method 1: Try Werkzeug with explicit parameters
            try:
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(
                    'admin123',
                    method='pbkdf2:sha256',
                    salt_length=8
                )
                admin_user.password_hash = password_hash
                print("✅ Used Werkzeug pbkdf2:sha256 method")

            except Exception as e:
                print(f"⚠️ Werkzeug method failed: {e}")
                # Method 2: Fallback to hashlib
                import hashlib
                import secrets
                salt = secrets.token_hex(16)
                password_hash = f"sha256${salt}${hashlib.sha256(('admin123' + salt).encode()).hexdigest()}"
                admin_user.password_hash = password_hash
                print("✅ Used fallback hashlib method")

            # Save changes
            db.session.commit()
            print("✅ Password saved to database")

            # Test the password immediately
            print("🧪 Testing password verification...")
            test_result = admin_user.check_password('admin123')

            if test_result:
                print("✅ Password verification test PASSED")
                print("   Username: admin")
                print("   Password: admin123")
                return True
            else:
                print("❌ Password verification test FAILED")
                return False

    except Exception as e:
        print(f"❌ Password fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_login_process():
    """Test the complete login process"""
    print("\n🔍 Testing complete login process...")

    try:
        from main import app
        from models import db, User

        with app.app_context():
            # Simulate login process
            username = 'admin'
            password = 'admin123'

            print(f"1️⃣ Looking up user: {username}")
            user = User.query.filter_by(username=username).first()

            if not user:
                print("❌ User not found")
                return False

            print(f"✅ User found: {user.username} ({user.email})")

            print(f"2️⃣ Checking password...")
            password_valid = user.check_password(password)

            if password_valid:
                print("✅ Password is valid")

                # Update last login
                from datetime import datetime
                user.last_login = datetime.utcnow()
                db.session.commit()
                print("✅ Last login updated")

                return True
            else:
                print("❌ Password is invalid")
                return False

    except Exception as e:
        print(f"❌ Login test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main password fix function"""
    print("=" * 60)
    print("🔧 PASSWORD FIX UTILITY")
    print("=" * 60)
    print("Fixing the 'Missing required argument digestmod' error")
    print()

    # Step 1: Fix admin password
    if not fix_admin_password():
        print("\n❌ Password fix failed!")
        return False

    # Step 2: Test login process
    if not test_login_process():
        print("\n❌ Login test failed!")
        return False

    print("\n" + "=" * 60)
    print("🎉 PASSWORD FIX COMPLETED!")
    print("=" * 60)
    print("\n✅ What was fixed:")
    print("   • Admin user password properly hashed")
    print("   • Password verification working")
    print("   • Login process tested")
    print("\n🔗 Try logging in now:")
    print("   1. Go to: http://localhost:5000/login")
    print("   2. Username: admin")
    print("   3. Password: admin123")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
