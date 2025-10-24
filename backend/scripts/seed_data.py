"""
Seed script to initialize database with default roles and admin user.
Run this after creating the database and running migrations.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import Role, User
from app.core.security import get_password_hash
from app.core.permissions import ROLE_PERMISSIONS, Role as RoleEnum


def create_roles(db: Session) -> dict:
    """Create default roles with permissions."""
    roles = {}
    
    role_definitions = {
        RoleEnum.EXECUTIVE: {
            "description": "Executive with full system access and approval authority",
            "permissions": {perm.value: True for perm in ROLE_PERMISSIONS[RoleEnum.EXECUTIVE]}
        },
        RoleEnum.SALES_REP: {
            "description": "Sales representative who creates order requests",
            "permissions": {perm.value: True for perm in ROLE_PERMISSIONS[RoleEnum.SALES_REP]}
        },
        RoleEnum.DECODER: {
            "description": "Decoder who maps order items to inventory SKUs",
            "permissions": {perm.value: True for perm in ROLE_PERMISSIONS[RoleEnum.DECODER]}
        },
        RoleEnum.QUOTER: {
            "description": "Quoter who generates quotations and invoices",
            "permissions": {perm.value: True for perm in ROLE_PERMISSIONS[RoleEnum.QUOTER]}
        },
        RoleEnum.INVENTORY_ADMIN: {
            "description": "Inventory administrator who manages stock and dispatches",
            "permissions": {perm.value: True for perm in ROLE_PERMISSIONS[RoleEnum.INVENTORY_ADMIN]}
        }
    }
    
    for role_enum, role_data in role_definitions.items():
        # Check if role already exists
        existing_role = db.query(Role).filter(Role.name == role_enum.value).first()
        if existing_role:
            print(f"Role '{role_enum.value}' already exists, skipping...")
            roles[role_enum.value] = existing_role
            continue
        
        role = Role(
            name=role_enum.value,
            description=role_data["description"],
            permissions=role_data["permissions"]
        )
        db.add(role)
        db.flush()
        roles[role_enum.value] = role
        print(f"Created role: {role_enum.value}")
    
    db.commit()
    return roles


def create_admin_user(db: Session, roles: dict) -> None:
    """Create default admin user with executive role."""
    admin_email = "admin@medicalequipment.com"
    
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        print(f"Admin user '{admin_email}' already exists, skipping...")
        return
    
    executive_role = roles.get(RoleEnum.EXECUTIVE.value)
    if not executive_role:
        print("Executive role not found, cannot create admin user")
        return
    
    admin_user = User(
        email=admin_email,
        hashed_password=get_password_hash("admin123"),  # Change this in production!
        full_name="System Administrator",
        role_id=executive_role.id,
        is_active=True
    )
    
    db.add(admin_user)
    db.commit()
    print(f"Created admin user: {admin_email} (password: admin123)")
    print("⚠️  IMPORTANT: Change the admin password immediately after first login!")


def create_sample_users(db: Session, roles: dict) -> None:
    """Create sample users for each role."""
    sample_users = [
        {
            "email": "sales@medicalequipment.com",
            "password": "sales123",
            "full_name": "John Sales",
            "role": RoleEnum.SALES_REP.value
        },
        {
            "email": "decoder@medicalequipment.com",
            "password": "decoder123",
            "full_name": "Jane Decoder",
            "role": RoleEnum.DECODER.value
        },
        {
            "email": "quoter@medicalequipment.com",
            "password": "quoter123",
            "full_name": "Mike Quoter",
            "role": RoleEnum.QUOTER.value
        },
        {
            "email": "inventory@medicalequipment.com",
            "password": "inventory123",
            "full_name": "Sarah Inventory",
            "role": RoleEnum.INVENTORY_ADMIN.value
        }
    ]
    
    for user_data in sample_users:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            print(f"User '{user_data['email']}' already exists, skipping...")
            continue
        
        role = roles.get(user_data["role"])
        if not role:
            print(f"Role '{user_data['role']}' not found, skipping user {user_data['email']}")
            continue
        
        user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=user_data["full_name"],
            role_id=role.id,
            is_active=True
        )
        
        db.add(user)
        print(f"Created user: {user_data['email']} (password: {user_data['password']})")
    
    db.commit()


def init_db() -> None:
    """Initialize database with seed data."""
    print("Starting database initialization...")
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Create roles
        print("\nCreating roles...")
        roles = create_roles(db)
        
        # Create admin user
        print("\nCreating admin user...")
        create_admin_user(db, roles)
        
        # Create sample users
        print("\nCreating sample users...")
        create_sample_users(db, roles)
        
        print("\n✅ Database initialization completed successfully!")
        print("\nDefault credentials:")
        print("  Admin: admin@medicalequipment.com / admin123")
        print("  Sales: sales@medicalequipment.com / sales123")
        print("  Decoder: decoder@medicalequipment.com / decoder123")
        print("  Quoter: quoter@medicalequipment.com / quoter123")
        print("  Inventory: inventory@medicalequipment.com / inventory123")
        print("\n⚠️  Remember to change these passwords in production!")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
