"""
Update quoter role permissions to include customer:create
Run this script once to update the database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal
from app.models.user import Role
import json

def update_quoter_permissions():
    db = SessionLocal()
    try:
        # Find the quoter role
        quoter_role = db.query(Role).filter(Role.name == 'quoter').first()
        
        if not quoter_role:
            print("Quoter role not found!")
            return
        
        # Get current permissions
        current_permissions = quoter_role.permissions or {}
        print(f"Current permissions: {current_permissions}")
        
        # Add customer:create permission
        current_permissions['customer:create'] = True
        
        # Update the role - force a new dict to trigger SQLAlchemy change detection
        quoter_role.permissions = dict(current_permissions)
        
        # Mark the attribute as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(quoter_role, 'permissions')
        
        db.commit()
        db.refresh(quoter_role)
        
        print(f"✅ Updated quoter role permissions: {quoter_role.permissions}")
        print("Quoters can now create customers!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_quoter_permissions()
