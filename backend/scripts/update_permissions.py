"""
Script to update role permissions in the database.
Run this after modifying permissions in permissions.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import Role
from app.core.permissions import ROLE_PERMISSIONS, Role as RoleEnum


def update_role_permissions():
    """Update all role permissions in the database."""
    db = SessionLocal()
    
    try:
        print("Updating role permissions...")
        
        for role_enum in RoleEnum:
            # Get the role from database
            db_role = db.query(Role).filter(Role.name == role_enum.value).first()
            
            if not db_role:
                print(f"⚠️  Role '{role_enum.value}' not found in database, skipping...")
                continue
            
            # Get updated permissions from code
            new_permissions = {perm.value: True for perm in ROLE_PERMISSIONS[role_enum]}
            
            # Update the role
            db_role.permissions = new_permissions
            print(f"✅ Updated permissions for role: {role_enum.value}")
            print(f"   Permissions: {list(new_permissions.keys())}")
        
        db.commit()
        print("\n✅ All role permissions updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating permissions: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_role_permissions()
