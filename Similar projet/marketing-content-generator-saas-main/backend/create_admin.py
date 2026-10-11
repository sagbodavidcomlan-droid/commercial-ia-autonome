"""
Create Admin User Script
Run this script to create an admin user in the database
"""
import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.core.database import Base

def create_admin_user():
    """Create an admin user in the database"""

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
            print(f"   To reset password, delete the user first or use a different email")
            return False

        # Create admin user
        hashed_password = get_password_hash(admin_password)
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password,
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
        print("⚠️  IMPORTANT: Save these credentials securely!")
        print("   You can now login at: http://localhost:3000/login")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
