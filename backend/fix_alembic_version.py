"""
Fix alembic version in database
"""
from app.db.session import engine
from sqlalchemy import text

def fix_alembic_version():
    with engine.connect() as conn:
        # Check current version
        result = conn.execute(text('SELECT version_num FROM alembic_version'))
        current = result.fetchone()
        print(f"Current version in database: {current[0] if current else 'None'}")
        
        # Update to the last valid migration before our new one
        conn.execute(text("UPDATE alembic_version SET version_num = 'b1c2d3e4f5g6'"))
        conn.commit()
        print("Updated version to: b1c2d3e4f5g6 (add_attachments_table)")
        
        # Verify
        result = conn.execute(text('SELECT version_num FROM alembic_version'))
        new_version = result.fetchone()
        print(f"New version in database: {new_version[0]}")

if __name__ == "__main__":
    fix_alembic_version()
