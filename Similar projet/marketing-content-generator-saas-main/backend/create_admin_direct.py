"""
Create Admin User Directly - Workaround for bcrypt issue
"""
import bcrypt
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.user import User

def create_admin_user():
    """Create an admin user in the database using bcrypt directly"""

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Admin credentials
        admin_email = "admin@marketgen.ai"
        admin_password = "Admin123"
        admin_name = "Admin User"

        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            print(f"❌ Admin user already exists with email: {admin_email}")
            print(f"   Deleting and recreating...")
            db.delete(existing_admin)
            db.commit()

        # Hash password using bcrypt directly
        password_bytes = admin_password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        hashed_password_str = hashed_password.decode('utf-8')

        # Create admin user
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password_str,
            full_name=admin_name
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("=" * 60)
        print("✅ ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Email:    {admin_email}")
        print(f"Password: {admin_password}")
        print(f"Name:     {admin_name}")
        print(f"User ID:  {admin_user.id}")
        print("=" * 60)
        print("   You can now login at: http://localhost:3000/login")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
