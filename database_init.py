#!/usr/bin/env python3
"""
Safe database initialization script with CASCADE support
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def reset_database_safely():
    """Safely reset database by dropping with CASCADE"""
    print("🗑️ Safely resetting database...")

    try:
        from main import app
        from models import db

        with app.app_context():
            # Get database engine
            engine = db.engine

            # Drop all tables and dependent objects with CASCADE
            print("   Dropping all tables with CASCADE...")

            # SQL to drop all tables with CASCADE
            drop_sql = """
            DO $$ DECLARE
                r RECORD;
            BEGIN
                -- Drop all views first
                FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.viewname) || ' CASCADE';
                END LOOP;

                -- Drop all tables with CASCADE
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;

                -- Drop all sequences
                FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                END LOOP;
            END $$;
            """

            # Execute the drop SQL
            with engine.connect() as conn:
                conn.execute(db.text(drop_sql))
                conn.commit()

            print("✅ All database objects dropped successfully")
            return True

    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

def create_fresh_database():
    """Create fresh database tables"""
    print("🆕 Creating fresh database structure...")

    try:
        from main import app
        from models import db, User, Project, Document

        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")

            # Verify tables were created
            tables = db.engine.table_names()
            print(f"   Created tables: {', '.join(tables)}")

            return True

    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

def create_default_data():
    """Create default admin user and sample data"""
    print("👤 Creating default data...")

    try:
        from main import app
        from models import db, User, Project

        with app.app_context():
            # Create default admin user
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@tenderanalysis.com',
                    full_name='System Administrator',
                    role='admin'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)

                # Create a sample project
                sample_project = Project(
                    name='Sample RFP Project',
                    description='A sample project for testing the tender analysis system',
                    status='active',
                    user_id=admin_user.id
                )
                db.session.add(sample_project)

                # Create Temenos as strategic partner
                from models import Partner
                temenos_partner = Partner.query.filter_by(name='Temenos').first()
                if not temenos_partner:
                    temenos_partner = Partner(
                        name='Temenos',
                        company_type='STRATEGIC',
                        status='PREFERRED',
                        description='Strategic partner for core banking and financial services solutions. ITSS Global is a certified Temenos implementation partner.',
                        website='https://www.temenos.com',
                        primary_contact='Partnership Manager',
                        contact_email='partnerships@temenos.com',
                        revenue_share_percentage=0.0,  # Strategic partnership
                        discount_level=15.0,  # Preferred partner discount
                        support_level='ENTERPRISE',
                        capabilities_summary='Temenos is the world leader in banking software, providing core banking, payments, fund management and wealth management solutions.',
                        solution_categories=['Core Banking', 'Digital Banking', 'Payments', 'Fund Management', 'Wealth Management', 'Regulatory Compliance'],
                        technology_stack=['Temenos Transact', 'Temenos Infinity', 'Temenos Fund Administration', 'Cloud Native', 'API First', 'Microservices'],
                        industry_focus=['Banking', 'Financial Services', 'Insurance', 'FinTech', 'Capital Markets'],
                        competitive_advantages=['Market Leader', 'Cloud Native', 'API First', 'Proven Implementation', 'Global Presence'],
                        scrape_status='SUCCESS'
                    )
                    db.session.add(temenos_partner)
                    print("✅ Temenos strategic partner created")
                
                db.session.commit()

                print("✅ Default admin user created:")
                print("   Username: admin")
                print("   Password: admin123")
                print("   ⚠️ IMPORTANT: Change password in production!")
                print("✅ Sample project created")
                print("✅ Temenos strategic partner configured")
            else:
                print("✅ Admin user already exists")

            return True

    except Exception as e:
        print(f"❌ Default data creation failed: {e}")
        db.session.rollback()
        return False

def verify_database():
    """Verify database setup"""
    print("🔍 Verifying database setup...")

    try:
        from main import app
        from models import db, User, Project, Document

        with app.app_context():
            # Check if we can query tables
            user_count = User.query.count()
            project_count = Project.query.count()
            document_count = Document.query.count()

            print(f"✅ Database verification successful:")
            print(f"   Users: {user_count}")
            print(f"   Projects: {project_count}")
            print(f"   Documents: {document_count}")

            # Test a simple join query
            projects_with_users = db.session.query(Project, User).join(User).all()
            print(f"   Projects with users: {len(projects_with_users)}")

            return True

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main initialization function"""
    print("=" * 60)
    print("🚀 TENDER ANALYSIS SYSTEM - DATABASE INITIALIZATION")
    print("=" * 60)

    # Step 1: Reset database safely
    if not reset_database_safely():
        print("❌ Database reset failed!")
        return False

    # Step 2: Create fresh database structure
    if not create_fresh_database():
        print("❌ Fresh database creation failed!")
        return False

    # Step 3: Create default data
    if not create_default_data():
        print("❌ Default data creation failed!")
        return False

    # Step 4: Verify everything works
    if not verify_database():
        print("❌ Database verification failed!")
        return False

    print("\n" + "=" * 60)
    print("🎉 DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\n🔗 Next steps:")
    print("   1. Access: http://localhost:5000")
    print("   2. Login: admin / admin123")
    print("   3. Start creating projects and uploading documents")
    print("   4. Monitor with: docker-compose logs -f web")
    print("\n📊 To check system status:")
    print("   • Health: curl http://localhost:5000/health")
    print("   • DB Test: curl http://localhost:5000/test-db")
    print("   • Redis Test: curl http://localhost:5000/test-redis")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Initialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
