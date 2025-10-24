"""
Seed script to add sample customers to the database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.user import User

def seed_customers():
    """Create sample customers."""
    db = SessionLocal()
    
    try:
        # Get admin user for created_by
        admin = db.query(User).filter(User.email == 'admin@medicalequipment.com').first()
        
        sample_customers = [
            {
                'name': 'Apollo Hospitals',
                'hospital_name': 'Apollo Hospitals',
                'contact_person': 'Dr. Ramesh Kumar',
                'email': 'procurement@apollohospitals.com',
                'phone': '9876543210',
                'address': '21, Greams Lane, Off Greams Road',
                'city': 'Chennai',
                'state': 'Tamil Nadu',
                'pincode': '600006',
                'gst_number': '33AAAAA0000A1Z5',
            },
            {
                'name': 'Fortis Healthcare',
                'hospital_name': 'Fortis Healthcare',
                'contact_person': 'Ms. Priya Sharma',
                'email': 'supplies@fortishealthcare.com',
                'phone': '9876543211',
                'address': 'Sector 62, Phase VIII',
                'city': 'Mohali',
                'state': 'Punjab',
                'pincode': '160062',
                'gst_number': '03BBBBB1111B2Z6',
            },
            {
                'name': 'Max Healthcare',
                'hospital_name': 'Max Healthcare',
                'contact_person': 'Mr. Anil Verma',
                'email': 'procurement@maxhealthcare.com',
                'phone': '9876543212',
                'address': '1, Press Enclave Road, Saket',
                'city': 'New Delhi',
                'state': 'Delhi',
                'pincode': '110017',
                'gst_number': '07CCCCC2222C3Z7',
            },
            {
                'name': 'Manipal Hospitals',
                'hospital_name': 'Manipal Hospitals',
                'contact_person': 'Dr. Suresh Reddy',
                'email': 'purchase@manipalhospitals.com',
                'phone': '9876543213',
                'address': '98, HAL Airport Road',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'pincode': '560017',
                'gst_number': '29DDDDD3333D4Z8',
            },
            {
                'name': 'Narayana Health',
                'hospital_name': 'Narayana Health',
                'contact_person': 'Ms. Lakshmi Iyer',
                'email': 'supplies@narayanahealth.org',
                'phone': '9876543214',
                'address': '258/A, Bommasandra Industrial Area',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'pincode': '560099',
                'gst_number': '29EEEEE4444E5Z9',
            },
            {
                'name': 'Medanta - The Medicity',
                'hospital_name': 'Medanta - The Medicity',
                'contact_person': 'Mr. Rajesh Gupta',
                'email': 'procurement@medanta.org',
                'phone': '9876543215',
                'address': 'Sector 38, Near Subhash Chowk',
                'city': 'Gurugram',
                'state': 'Haryana',
                'pincode': '122001',
                'gst_number': '06FFFFF5555F6Z0',
            },
            {
                'name': 'Kokilaben Dhirubhai Ambani Hospital',
                'hospital_name': 'Kokilaben Dhirubhai Ambani Hospital',
                'contact_person': 'Dr. Meera Patel',
                'email': 'supplies@kokilabenhospital.com',
                'phone': '9876543216',
                'address': 'Rao Saheb Achutrao Patwardhan Marg',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'pincode': '400053',
                'gst_number': '27GGGGG6666G7Z1',
            },
            {
                'name': 'Ruby Hall Clinic',
                'hospital_name': 'Ruby Hall Clinic',
                'contact_person': 'Mr. Vikram Desai',
                'email': 'purchase@rubyhall.com',
                'phone': '9876543217',
                'address': '40, Sassoon Road',
                'city': 'Pune',
                'state': 'Maharashtra',
                'pincode': '411001',
                'gst_number': '27HHHHH7777H8Z2',
            },
        ]
        
        for customer_data in sample_customers:
            # Check if customer already exists
            existing = db.query(Customer).filter(
                Customer.hospital_name == customer_data['hospital_name']
            ).first()
            
            if existing:
                print(f"Customer '{customer_data['hospital_name']}' already exists, skipping...")
                continue
            
            customer = Customer(**customer_data)
            if admin:
                customer.set_audit_fields(admin.id, is_create=True)
            
            db.add(customer)
            print(f"✅ Created customer: {customer_data['hospital_name']}")
        
        db.commit()
        print(f"\n✅ Successfully seeded {len(sample_customers)} customers!")
        
    except Exception as e:
        print(f"❌ Error seeding customers: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_customers()
