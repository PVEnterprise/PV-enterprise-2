"""
Add payment permissions to executive role in the database.
Run this once after the payments migration to enable the Accounts module for executives.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal
from app.models.user import Role
from sqlalchemy.orm.attributes import flag_modified

PAYMENT_PERMISSIONS = {
    "payment:create": True,
    "payment:read": True,
    "payment:update": True,
    "payment:delete": True,
}

def update_executive_permissions():
    db = SessionLocal()
    try:
        executive_role = db.query(Role).filter(Role.name == 'executive').first()
        if not executive_role:
            print("Executive role not found!")
            return

        current = dict(executive_role.permissions or {})
        print(f"Current executive permissions count: {len(current)}")

        current.update(PAYMENT_PERMISSIONS)
        executive_role.permissions = current
        flag_modified(executive_role, 'permissions')
        db.commit()
        db.refresh(executive_role)
        print("✅ Executive role now has payment permissions:")
        for k in PAYMENT_PERMISSIONS:
            print(f"   {k}: {executive_role.permissions.get(k)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_executive_permissions()
