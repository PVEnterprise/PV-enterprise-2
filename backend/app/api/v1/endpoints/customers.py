"""
Customer management endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
import pandas as pd
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_current_user, PermissionChecker
from app.core.permissions import Permission
from app.models.user import User
from app.models.customer import Customer


router = APIRouter()


class CustomerBase(BaseModel):
    name: str = Field(..., max_length=255)
    hospital_name: str = Field(..., max_length=255)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gst_number: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    hospital_name: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    gst_number: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_CREATE))
):
    """Create a new customer."""
    customer = Customer(**customer_data.model_dump(), created_by=current_user.id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_READ))
):
    """List customers with search."""
    query = db.query(Customer)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Customer.hospital_name.ilike(search_term)) |
            (Customer.name.ilike(search_term)) |
            (Customer.gst_number.ilike(search_term))
        )
    
    query = query.order_by(Customer.hospital_name)
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_READ))
):
    """Get customer details."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_UPDATE))
):
    """Update customer details."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_DELETE))
):
    """Delete a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    return None


@router.post("/import-excel")
async def import_customers_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(Permission.CUSTOMER_CREATE))
):
    """
    Import customers from Excel file.
    
    Expected columns:
    - Hospital Name (required)
    - Contact Person (required)
    - Email
    - Phone (required)
    - Address (required)
    - City (required)
    - State (required)
    - Pincode (required)
    - GST Number (required)
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Column mapping
        column_mapping = {
            'hospital_name': ['hospital_name', 'hospital', 'name'],
            'contact_person': ['contact_person', 'contact', 'person'],
            'email': ['email', 'e-mail', 'email_address'],
            'phone': ['phone', 'phone_number', 'mobile', 'contact_number'],
            'address': ['address', 'location'],
            'city': ['city'],
            'state': ['state'],
            'pincode': ['pincode', 'pin_code', 'pin', 'postal_code'],
            'gst_number': ['gst_number', 'gst', 'gstin', 'gst_no']
        }
        
        # Find actual column names
        actual_columns = {}
        for field, possible_names in column_mapping.items():
            for col in df.columns:
                if col in possible_names:
                    actual_columns[field] = col
                    break
        
        # Check required columns
        required_fields = ['hospital_name', 'contact_person', 'phone', 'address', 'city', 'state', 'pincode', 'gst_number']
        missing_fields = [field for field in required_fields if field not in actual_columns]
        
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_fields)}"
            )
        
        # Import customers
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Extract data
                hospital_name = str(row[actual_columns['hospital_name']]).strip()
                contact_person = str(row[actual_columns['contact_person']]).strip()
                phone = str(row[actual_columns['phone']]).strip()
                address = str(row[actual_columns['address']]).strip()
                city = str(row[actual_columns['city']]).strip()
                state = str(row[actual_columns['state']]).strip()
                pincode = str(row[actual_columns['pincode']]).strip()
                gst_number = str(row[actual_columns['gst_number']]).strip()
                
                # Optional email
                email = None
                if 'email' in actual_columns and pd.notna(row[actual_columns['email']]):
                    email = str(row[actual_columns['email']]).strip()
                
                # Skip if hospital name is empty
                if not hospital_name or hospital_name == 'nan':
                    skipped_count += 1
                    continue
                
                # Check if customer already exists
                existing = db.query(Customer).filter(
                    Customer.hospital_name == hospital_name
                ).first()
                
                if existing:
                    skipped_count += 1
                    errors.append(f"Row {index + 2}: Customer '{hospital_name}' already exists")
                    continue
                
                # Create customer
                customer = Customer(
                    hospital_name=hospital_name,
                    name=contact_person,
                    contact_person=contact_person,
                    email=email,
                    phone=phone,
                    address=address,
                    city=city,
                    state=state,
                    pincode=pincode,
                    gst_number=gst_number,
                    created_by=current_user.id
                )
                
                db.add(customer)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                skipped_count += 1
        
        # Commit all changes
        db.commit()
        
        return {
            "message": "Import completed",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors if errors else None
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Excel file is empty"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing Excel file: {str(e)}"
        )


@router.get("/export/template")
def download_import_template(
    current_user: User = Depends(get_current_user)
):
    """Download Excel template for customer import."""
    # Create template dataframe
    template_data = {
        'Hospital Name': ['Apollo Hospitals', 'KIMS Hospital'],
        'Contact Person': ['Dr. Meena Sharma', 'Dr. Rekha Iyer'],
        'Email': ['meena.sharma@apollohospitals.com', 'rekha.iyer@kimshospitals.com'],
        'Phone': ['9845012345', '9966334455'],
        'Address': ['No. 21, Greams Lane, Off Greams Road', '1-8-31/1, Minister Road, Secunderabad'],
        'City': ['Chennai', 'Hyderabad'],
        'State': ['Tamil Nadu', 'Telangana'],
        'Pincode': ['600006', '500003'],
        'GST Number': ['33AAACA1234A1Z7', '36AAACK1234F1Z2']
    }
    
    df = pd.DataFrame(template_data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Customers')
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=customer_import_template.xlsx"
        }
    )
