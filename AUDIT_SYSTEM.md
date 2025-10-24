# Audit System & Reusable Components

## ✅ Implementation Complete

A comprehensive audit tracking system and reusable form/list components have been implemented.

---

## 🔍 Audit Tracking System

### Database Level Audit Fields

Every record in the system now tracks:

| Field | Type | Description | Default on Create |
|-------|------|-------------|-------------------|
| `created_at` | DateTime | When record was created | Current timestamp |
| `updated_at` | DateTime | When record was last updated | Same as created_at |
| `created_by` | UUID | User who created the record | Current user ID |
| `updated_by` | UUID | User who last updated the record | Same as created_by |

### How It Works

**On Record Creation:**
```python
# Backend automatically sets:
record.created_at = datetime.utcnow()
record.updated_at = datetime.utcnow()  # Same as created_at initially
record.created_by = current_user.id
record.updated_by = current_user.id    # Same as created_by initially
```

**On Record Update:**
```python
# Backend automatically updates:
record.updated_at = datetime.utcnow()
record.updated_by = current_user.id
# created_at and created_by remain unchanged
```

### Tables with Audit Tracking

All 15 tables now have audit fields:

- ✅ roles
- ✅ users
- ✅ customers
- ✅ inventory
- ✅ orders
- ✅ order_items
- ✅ quotations
- ✅ quotation_items
- ✅ invoices
- ✅ invoice_items
- ✅ approvals
- ✅ audit_logs
- ✅ notifications
- ✅ dispatches
- ✅ dispatch_items

---

## 🎨 Reusable Components

### 1. DynamicForm Component

**Location**: `frontend/src/components/common/DynamicForm.tsx`

A flexible, reusable form component for creating and updating any record type.

#### Features:
- ✅ Dynamic field generation from configuration
- ✅ Built-in validation (required, pattern, min/max)
- ✅ Support for multiple field types
- ✅ Error handling and display
- ✅ Loading states
- ✅ Create and Edit modes
- ✅ Modal-based UI

#### Supported Field Types:
- `text` - Text input
- `email` - Email input with validation
- `number` - Number input with min/max
- `textarea` - Multi-line text
- `select` - Dropdown with options
- `date` - Date picker
- `checkbox` - Boolean checkbox

#### Usage Example:

```tsx
import DynamicForm, { FormField } from '@/components/common/DynamicForm';

const customerFields: FormField[] = [
  {
    name: 'hospital_name',
    label: 'Hospital Name',
    type: 'text',
    required: true,
    placeholder: 'Enter hospital name',
  },
  {
    name: 'email',
    label: 'Email',
    type: 'email',
    required: true,
    validation: {
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      message: 'Please enter a valid email',
    },
  },
  {
    name: 'phone',
    label: 'Phone',
    type: 'text',
    required: true,
    validation: {
      pattern: /^\d{10}$/,
      message: 'Phone must be 10 digits',
    },
  },
  {
    name: 'gst_number',
    label: 'GST Number',
    type: 'text',
    placeholder: 'Enter GST number',
  },
  {
    name: 'city',
    label: 'City',
    type: 'text',
    required: true,
  },
  {
    name: 'state',
    label: 'State',
    type: 'select',
    required: true,
    options: [
      { value: 'maharashtra', label: 'Maharashtra' },
      { value: 'karnataka', label: 'Karnataka' },
      // ... more states
    ],
  },
];

function CustomersPage() {
  const [showForm, setShowForm] = useState(false);
  
  const handleSubmit = async (data: Record<string, any>) => {
    await api.createCustomer(data);
    setShowForm(false);
    // Refresh list
  };

  return (
    <>
      <button onClick={() => setShowForm(true)}>Add Customer</button>
      
      {showForm && (
        <DynamicForm
          title="Customer"
          fields={customerFields}
          onSubmit={handleSubmit}
          onCancel={() => setShowForm(false)}
          submitLabel="Create Customer"
        />
      )}
    </>
  );
}
```

#### Edit Mode:

```tsx
<DynamicForm
  title="Customer"
  fields={customerFields}
  onSubmit={handleUpdate}
  onCancel={() => setShowForm(false)}
  submitLabel="Update Customer"
  initialData={selectedCustomer}  // Pre-fill with existing data
  isEdit={true}                    // Show "Edit" in title
/>
```

---

### 2. DataTable Component

**Location**: `frontend/src/components/common/DataTable.tsx`

A powerful, reusable table component for displaying lists with actions and audit info.

#### Features:
- ✅ Dynamic column configuration
- ✅ Custom cell rendering
- ✅ Row actions (view, edit, delete)
- ✅ Automatic audit info display
- ✅ Loading states
- ✅ Empty states
- ✅ Row click handling
- ✅ Conditional action visibility

#### Usage Example:

```tsx
import DataTable, { Column, commonActions } from '@/components/common/DataTable';

interface Customer {
  id: string;
  hospital_name: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  created_at: string;
  updated_at: string;
  created_by_name: string;
  updated_by_name: string;
}

const columns: Column<Customer>[] = [
  {
    key: 'hospital_name',
    label: 'Hospital Name',
    sortable: true,
  },
  {
    key: 'email',
    label: 'Email',
  },
  {
    key: 'phone',
    label: 'Phone',
  },
  {
    key: 'city',
    label: 'City',
    render: (value, row) => `${value}, ${row.state}`,
  },
];

function CustomersPage() {
  const { data: customers, isLoading } = useQuery(['customers'], fetchCustomers);
  const canEdit = user?.role?.permissions?.['customer:update'];
  const canDelete = user?.role?.permissions?.['customer:delete'];

  return (
    <DataTable
      data={customers || []}
      columns={columns}
      isLoading={isLoading}
      emptyMessage="No customers found"
      showAuditInfo={true}  // Show created/updated info
      actions={[
        commonActions.view((row) => handleView(row)),
        commonActions.edit(
          (row) => handleEdit(row),
          () => canEdit  // Only show if user has permission
        ),
        commonActions.delete(
          (row) => handleDelete(row),
          () => canDelete
        ),
      ]}
    />
  );
}
```

#### Audit Info Display:

The table automatically shows audit information below the first column:

```
Hospital Name: ABC Medical Center
Created: 10/24/2025, 1:30 PM by Admin User
Updated: 10/24/2025, 2:45 PM by John Sales
```

---

## 🔧 Backend Implementation

### BaseModel with Audit Support

**File**: `backend/app/db/base.py`

```python
class BaseModel(Base):
    """Base model with audit tracking."""
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    def set_audit_fields(self, user_id: UUID, is_create: bool = False):
        """Set audit fields for create or update operations."""
        if is_create:
            self.created_by = user_id
            self.updated_by = user_id  # Default to created_by
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
        else:
            self.updated_by = user_id
            self.updated_at = datetime.utcnow()
```

### Using Audit Fields in Endpoints

```python
@router.post("/customers", response_model=CustomerResponse)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create customer
    customer = Customer(**customer_data.dict())
    
    # Set audit fields
    customer.set_audit_fields(current_user.id, is_create=True)
    
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    # Update fields
    for key, value in customer_data.dict(exclude_unset=True).items():
        setattr(customer, key, value)
    
    # Set audit fields
    customer.set_audit_fields(current_user.id, is_create=False)
    
    db.commit()
    db.refresh(customer)
    
    return customer
```

---

## 📊 Complete Implementation Example

### Customer Management with Audit

**CustomersPage.tsx**:

```tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/context/AuthContext';
import DynamicForm, { FormField } from '@/components/common/DynamicForm';
import DataTable, { Column, commonActions } from '@/components/common/DataTable';
import api from '@/services/api';

const customerFields: FormField[] = [
  { name: 'hospital_name', label: 'Hospital Name', type: 'text', required: true },
  { name: 'contact_person', label: 'Contact Person', type: 'text', required: true },
  { name: 'email', label: 'Email', type: 'email', required: true },
  { name: 'phone', label: 'Phone', type: 'text', required: true },
  { name: 'address', label: 'Address', type: 'textarea' },
  { name: 'city', label: 'City', type: 'text', required: true },
  { name: 'state', label: 'State', type: 'text', required: true },
  { name: 'gst_number', label: 'GST Number', type: 'text' },
];

const columns: Column<Customer>[] = [
  { key: 'hospital_name', label: 'Hospital Name' },
  { key: 'contact_person', label: 'Contact' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
];

export default function CustomersPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: customers, isLoading } = useQuery(['customers'], api.getCustomers);

  const createMutation = useMutation({
    mutationFn: api.createCustomer,
    onSuccess: () => {
      queryClient.invalidateQueries(['customers']);
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.updateCustomer(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['customers']);
      setShowForm(false);
      setEditingCustomer(null);
    },
  });

  const canCreate = user?.role?.permissions?.['customer:create'];
  const canEdit = user?.role?.permissions?.['customer:update'];
  const canDelete = user?.role?.permissions?.['customer:delete'];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Customers</h1>
        {canCreate && (
          <button onClick={() => setShowForm(true)} className="btn btn-primary">
            Add Customer
          </button>
        )}
      </div>

      <DataTable
        data={customers || []}
        columns={columns}
        isLoading={isLoading}
        showAuditInfo={true}
        actions={[
          commonActions.edit(
            (row) => {
              setEditingCustomer(row);
              setShowForm(true);
            },
            () => canEdit
          ),
          commonActions.delete(
            (row) => handleDelete(row),
            () => canDelete
          ),
        ]}
      />

      {showForm && (
        <DynamicForm
          title="Customer"
          fields={customerFields}
          onSubmit={(data) => {
            if (editingCustomer) {
              updateMutation.mutate({ id: editingCustomer.id, data });
            } else {
              createMutation.mutate(data);
            }
          }}
          onCancel={() => {
            setShowForm(false);
            setEditingCustomer(null);
          }}
          initialData={editingCustomer}
          isEdit={!!editingCustomer}
          isLoading={createMutation.isLoading || updateMutation.isLoading}
        />
      )}
    </div>
  );
}
```

---

## ✅ Benefits

### 1. Audit Trail
- **Who**: Track which user created/modified each record
- **When**: Timestamp for every change
- **Accountability**: Full audit history
- **Compliance**: Meet regulatory requirements

### 2. Reusability
- **DRY Principle**: Write once, use everywhere
- **Consistency**: Same UI/UX across all forms
- **Maintainability**: Fix bugs in one place
- **Scalability**: Easy to add new entities

### 3. Developer Experience
- **Quick Implementation**: Minutes instead of hours
- **Type Safety**: Full TypeScript support
- **Validation**: Built-in field validation
- **Flexibility**: Highly customizable

---

## 🚀 Next Steps

### To Use These Components:

1. **Define your fields** for the entity
2. **Define your columns** for the table
3. **Use DynamicForm** for create/edit
4. **Use DataTable** for listing
5. **Audit tracking** happens automatically!

### Example for Inventory:

```tsx
const inventoryFields: FormField[] = [
  { name: 'sku', label: 'SKU', type: 'text', required: true },
  { name: 'item_name', label: 'Item Name', type: 'text', required: true },
  { name: 'unit_price', label: 'Unit Price', type: 'number', required: true },
  { name: 'stock_quantity', label: 'Stock Quantity', type: 'number', required: true },
  // ... more fields
];

// Use DynamicForm and DataTable as shown above
```

---

## 📝 Summary

✅ **Audit System**: All tables track created_at, updated_at, created_by, updated_by  
✅ **DynamicForm**: Reusable form component with validation  
✅ **DataTable**: Reusable table component with audit info display  
✅ **Database Migration**: Applied successfully  
✅ **Backend Helper**: `set_audit_fields()` method  
✅ **Frontend Components**: Ready to use  

**Status**: ✅ **Complete audit tracking and reusable components implemented!**
