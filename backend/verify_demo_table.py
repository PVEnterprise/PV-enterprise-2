"""
Verify demo_requests table was created
"""
from app.db.session import engine
from sqlalchemy import text

def verify_table():
    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'demo_requests'
        """))
        table = result.fetchone()
        
        if table:
            print("✅ demo_requests table exists!")
            
            # Get columns
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'demo_requests'
                ORDER BY ordinal_position
            """))
            
            print("\nTable columns:")
            for row in result:
                nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                print(f"  - {row[0]}: {row[1]} ({nullable})")
        else:
            print("❌ demo_requests table does not exist")

if __name__ == "__main__":
    verify_table()
