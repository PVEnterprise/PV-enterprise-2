# Database Schema & Entity Relationship Diagram

## Entity Relationship Diagram (ERD)

```
┌─────────────────┐
│     Users       │
├─────────────────┤
│ id (PK)         │
│ email           │
│ hashed_password │
│ full_name       │
│ role_id (FK)    │──┐
│ is_active       │  │
│ created_at      │  │
│ updated_at      │  │
└─────────────────┘  │
                     │
                     ↓
              ┌─────────────────┐
              │     Roles       │
              ├─────────────────┤
              │ id (PK)         │
              │ name            │
              │ description     │
              │ permissions     │
              └─────────────────┘

┌─────────────────┐
│   Customers     │
├─────────────────┤
│ id (PK)         │
│ name            │
│ hospital_name   │
│ contact_person  │
│ email           │
│ phone           │
│ address         │
│ gst_number      │
│ created_by (FK) │──→ Users
│ created_at      │
│ updated_at      │
└─────────────────┘
        ↑
        │
        │
┌─────────────────┐
│     Orders      │
├─────────────────┤
│ id (PK)         │
│ order_number    │
│ customer_id(FK) │──┘
│ sales_rep_id(FK)│──→ Users
│ status          │
│ workflow_stage  │
│ priority        │
│ source          │
│ notes           │
│ created_at      │
│ updated_at      │
└─────────────────┘
        │
        │ 1:N
        ↓
┌─────────────────┐
│   OrderItems    │
├─────────────────┤
│ id (PK)         │
│ order_id (FK)   │──┘
│ item_desc       │
│ quantity        │
│ inventory_id(FK)│──┐
│ decoded_by (FK) │  │
│ unit_price      │  │
│ status          │  │
│ notes           │  │
│ created_at      │  │
│ updated_at      │  │
└─────────────────┘  │
                     │
                     ↓
              ┌─────────────────┐
              │   Inventory     │
              ├─────────────────┤
              │ id (PK)         │
              │ sku             │
              │ item_name       │
              │ description     │
              │ category        │
              │ manufacturer    │
              │ unit_price      │
              │ stock_quantity  │
              │ reorder_level   │
              │ is_active       │
              │ created_at      │
              │ updated_at      │
              └─────────────────┘
                     ↑
                     │
┌─────────────────┐ │
│   Quotations    │ │
├─────────────────┤ │
│ id (PK)         │ │
│ quote_number    │ │
│ order_id (FK)   │──→ Orders
│ created_by (FK) │──→ Users
│ status          │
│ subtotal        │
│ gst_rate        │
│ gst_amount      │
│ discount_pct    │
│ discount_amt    │
│ total_amount    │
│ valid_until     │
│ terms           │
│ notes           │
│ created_at      │
│ updated_at      │
└─────────────────┘
        │
        │ 1:N
        ↓
┌─────────────────┐
│ QuotationItems  │
├─────────────────┤
│ id (PK)         │
│ quotation_id(FK)│──┘
│ inventory_id(FK)│──┘
│ description     │
│ quantity        │
│ unit_price      │
│ line_total      │
│ created_at      │
└─────────────────┘

┌─────────────────┐
│    Invoices     │
├─────────────────┤
│ id (PK)         │
│ invoice_number  │
│ quotation_id(FK)│──→ Quotations
│ order_id (FK)   │──→ Orders
│ created_by (FK) │──→ Users
│ status          │
│ invoice_date    │
│ due_date        │
│ subtotal        │
│ gst_amount      │
│ total_amount    │
│ paid_amount     │
│ balance         │
│ payment_status  │
│ payment_terms   │
│ notes           │
│ created_at      │
│ updated_at      │
└─────────────────┘
        │
        │ 1:N
        ↓
┌─────────────────┐
│  InvoiceItems   │
├─────────────────┤
│ id (PK)         │
│ invoice_id (FK) │──┘
│ inventory_id(FK)│──→ Inventory
│ description     │
│ quantity        │
│ unit_price      │
│ line_total      │
│ created_at      │
└─────────────────┘

┌─────────────────┐
│   Approvals     │
├─────────────────┤
│ id (PK)         │
│ entity_type     │
│ entity_id       │
│ stage           │
│ approver_id(FK) │──→ Users
│ status          │
│ comments        │
│ approved_at     │
│ created_at      │
└─────────────────┘

┌─────────────────┐
│   AuditLogs     │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │──→ Users
│ action          │
│ entity_type     │
│ entity_id       │
│ old_values      │
│ new_values      │
│ ip_address      │
│ user_agent      │
│ created_at      │
└─────────────────┘

┌─────────────────┐
│ Notifications   │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │──→ Users
│ type            │
│ title           │
│ message         │
│ link            │
│ is_read         │
│ created_at      │
└─────────────────┘

┌─────────────────┐
│   Dispatches    │
├─────────────────┤
│ id (PK)         │
│ order_id (FK)   │──→ Orders
│ invoice_id (FK) │──→ Invoices
│ dispatch_number │
│ dispatch_date   │
│ courier_name    │
│ tracking_number │
│ status          │
│ notes           │
│ created_by (FK) │──→ Users
│ created_at      │
│ updated_at      │
└─────────────────┘
        │
        │ 1:N
        ↓
┌─────────────────┐
│ DispatchItems   │
├─────────────────┤
│ id (PK)         │
│ dispatch_id(FK) │──┘
│ inventory_id(FK)│──→ Inventory
│ quantity        │
│ created_at      │
└─────────────────┘
```

## Detailed Table Schemas

### 1. Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role_id);
```

**Purpose**: Store user authentication and profile information
**Key Fields**:
- `email`: Unique login identifier
- `hashed_password`: Bcrypt hashed password
- `role_id`: Foreign key to roles table for RBAC
- `is_active`: Soft delete flag

### 2. Roles Table
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_roles_name ON roles(name);
```

**Purpose**: Define user roles and their permissions
**Key Fields**:
- `name`: Role name (executive, sales_rep, decoder, quoter, inventory_admin)
- `permissions`: JSONB object storing granular permissions

**Sample Permissions Structure**:
```json
{
  "orders": ["create", "read", "update", "delete", "approve"],
  "inventory": ["read"],
  "quotations": ["read", "approve"],
  "dashboard": ["read"]
}
```

### 3. Customers Table
```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    hospital_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(20),
    gst_number VARCHAR(50),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_hospital ON customers(hospital_name);
CREATE INDEX idx_customers_gst ON customers(gst_number);
```

**Purpose**: Store hospital/customer information
**Key Fields**:
- `hospital_name`: Primary identifier for the customer
- `gst_number`: For tax compliance
- `created_by`: Tracks which user created the customer record

### 4. Orders Table
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id),
    sales_rep_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    workflow_stage VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    source VARCHAR(50),
    po_number VARCHAR(100),
    po_date DATE,
    po_amount DECIMAL(15, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_number ON orders(order_number);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_sales_rep ON orders(sales_rep_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_stage ON orders(workflow_stage);
```

**Purpose**: Track order lifecycle from creation to completion
**Key Fields**:
- `order_number`: Auto-generated unique identifier (e.g., ORD-2025-0001)
- `status`: Current status (draft, pending, approved, completed, cancelled)
- `workflow_stage`: Current workflow position (order_request, decoding, quotation, po_received, invoiced, dispatched)
- `priority`: Order urgency (low, medium, high, urgent)
- `source`: How order was received (email, whatsapp, phone, direct)

**Workflow Stages**:
1. `order_request` - Initial order created by sales rep
2. `decoding` - Being decoded by decoder
3. `decoding_approval` - Awaiting executive approval
4. `quotation` - Quotation being prepared
5. `quotation_approval` - Quotation awaiting approval
6. `quotation_sent` - Quotation sent to customer
7. `po_received` - Purchase order received
8. `po_approval` - PO awaiting approval
9. `inventory_check` - Stock availability check
10. `invoice_request` - Invoice being prepared
11. `invoice_approval` - Invoice awaiting approval
12. `invoiced` - Invoice sent
13. `dispatched` - Items dispatched
14. `completed` - Order fulfilled
15. `cancelled` - Order cancelled

### 5. OrderItems Table
```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    inventory_id UUID REFERENCES inventory(id),
    decoded_by UUID REFERENCES users(id),
    unit_price DECIMAL(15, 2),
    status VARCHAR(50) DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_inventory ON order_items(inventory_id);
CREATE INDEX idx_order_items_status ON order_items(status);
```

**Purpose**: Individual line items in orders
**Key Fields**:
- `item_description`: Original description from customer
- `inventory_id`: Mapped SKU (null until decoded)
- `decoded_by`: User who performed the decoding
- `status`: Item status (pending, decoded, approved, fulfilled, partial)

### 6. Inventory Table
```sql
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(100) UNIQUE NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    manufacturer VARCHAR(255),
    model_number VARCHAR(100),
    unit_price DECIMAL(15, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    available_quantity INTEGER GENERATED ALWAYS AS (stock_quantity - reserved_quantity) STORED,
    reorder_level INTEGER DEFAULT 10,
    unit_of_measure VARCHAR(50) DEFAULT 'piece',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_sku ON inventory(sku);
CREATE INDEX idx_inventory_category ON inventory(category);
CREATE INDEX idx_inventory_active ON inventory(is_active);
CREATE INDEX idx_inventory_stock ON inventory(stock_quantity);
```

**Purpose**: Product catalog and stock management
**Key Fields**:
- `sku`: Stock Keeping Unit (unique identifier)
- `stock_quantity`: Total physical stock
- `reserved_quantity`: Stock allocated to orders
- `available_quantity`: Computed field (stock - reserved)
- `reorder_level`: Threshold for low stock alerts

### 7. Quotations Table
```sql
CREATE TABLE quotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_number VARCHAR(50) UNIQUE NOT NULL,
    order_id UUID NOT NULL REFERENCES orders(id),
    created_by UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    subtotal DECIMAL(15, 2) NOT NULL,
    gst_rate DECIMAL(5, 2) DEFAULT 18.00,
    gst_amount DECIMAL(15, 2) NOT NULL,
    discount_percentage DECIMAL(5, 2) DEFAULT 0.00,
    discount_amount DECIMAL(15, 2) DEFAULT 0.00,
    total_amount DECIMAL(15, 2) NOT NULL,
    valid_until DATE,
    payment_terms TEXT,
    delivery_terms TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quotations_number ON quotations(quote_number);
CREATE INDEX idx_quotations_order ON quotations(order_id);
CREATE INDEX idx_quotations_status ON quotations(status);
```

**Purpose**: Store quotation details and pricing
**Key Fields**:
- `quote_number`: Auto-generated (e.g., QUO-2025-0001)
- `status`: draft, pending_approval, approved, sent, accepted, rejected
- `gst_rate`: GST percentage (default 18%)
- `valid_until`: Quotation expiry date

### 8. QuotationItems Table
```sql
CREATE TABLE quotation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quotation_id UUID NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    inventory_id UUID NOT NULL REFERENCES inventory(id),
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL,
    line_total DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quotation_items_quotation ON quotation_items(quotation_id);
CREATE INDEX idx_quotation_items_inventory ON quotation_items(inventory_id);
```

**Purpose**: Line items in quotations
**Key Fields**:
- `line_total`: quantity × unit_price

### 9. Invoices Table
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    quotation_id UUID REFERENCES quotations(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    created_by UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal DECIMAL(15, 2) NOT NULL,
    gst_amount DECIMAL(15, 2) NOT NULL,
    total_amount DECIMAL(15, 2) NOT NULL,
    paid_amount DECIMAL(15, 2) DEFAULT 0.00,
    balance DECIMAL(15, 2) GENERATED ALWAYS AS (total_amount - paid_amount) STORED,
    payment_status VARCHAR(50) DEFAULT 'unpaid',
    payment_terms TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_order ON invoices(order_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_payment_status ON invoices(payment_status);
```

**Purpose**: Billing documents and payment tracking
**Key Fields**:
- `invoice_number`: Auto-generated (e.g., INV-2025-0001)
- `payment_status`: unpaid, partial, paid, overdue
- `balance`: Computed field (total - paid)

### 10. InvoiceItems Table
```sql
CREATE TABLE invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    inventory_id UUID NOT NULL REFERENCES inventory(id),
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL,
    line_total DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX idx_invoice_items_inventory ON invoice_items(inventory_id);
```

### 11. Approvals Table
```sql
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    stage VARCHAR(100) NOT NULL,
    approver_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    comments TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_approvals_entity ON approvals(entity_type, entity_id);
CREATE INDEX idx_approvals_approver ON approvals(approver_id);
CREATE INDEX idx_approvals_status ON approvals(status);
```

**Purpose**: Track all approval workflows
**Key Fields**:
- `entity_type`: orders, quotations, invoices, po
- `entity_id`: ID of the entity being approved
- `stage`: Specific approval stage
- `status`: pending, approved, rejected, rework_required

### 12. AuditLogs Table
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

**Purpose**: Complete audit trail for compliance
**Key Fields**:
- `action`: create, update, delete, approve, reject
- `old_values`: Previous state (JSONB)
- `new_values`: New state (JSONB)

### 13. Notifications Table
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    link VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);
```

**Purpose**: In-app notifications for users
**Key Fields**:
- `type`: approval_request, status_update, alert, info
- `link`: Deep link to relevant entity

### 14. Dispatches Table
```sql
CREATE TABLE dispatches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_number VARCHAR(50) UNIQUE NOT NULL,
    order_id UUID NOT NULL REFERENCES orders(id),
    invoice_id UUID REFERENCES invoices(id),
    dispatch_date DATE NOT NULL,
    courier_name VARCHAR(255),
    tracking_number VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dispatches_number ON dispatches(dispatch_number);
CREATE INDEX idx_dispatches_order ON dispatches(order_id);
CREATE INDEX idx_dispatches_status ON dispatches(status);
```

**Purpose**: Track shipments and deliveries
**Key Fields**:
- `status`: pending, in_transit, delivered, returned

### 15. DispatchItems Table
```sql
CREATE TABLE dispatch_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_id UUID NOT NULL REFERENCES dispatches(id) ON DELETE CASCADE,
    inventory_id UUID NOT NULL REFERENCES inventory(id),
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dispatch_items_dispatch ON dispatch_items(dispatch_id);
CREATE INDEX idx_dispatch_items_inventory ON dispatch_items(inventory_id);
```

## Key Relationships

1. **Users → Roles**: Many-to-One (Each user has one role)
2. **Orders → Customers**: Many-to-One (Multiple orders per customer)
3. **Orders → Users (Sales Rep)**: Many-to-One
4. **OrderItems → Orders**: Many-to-One (Cascade delete)
5. **OrderItems → Inventory**: Many-to-One
6. **Quotations → Orders**: One-to-One or One-to-Many
7. **QuotationItems → Quotations**: Many-to-One (Cascade delete)
8. **Invoices → Orders**: One-to-Many (Partial invoicing)
9. **Approvals → Multiple Entities**: Polymorphic relationship
10. **AuditLogs → Multiple Entities**: Polymorphic relationship

## Data Integrity Constraints

1. **Foreign Key Constraints**: All relationships enforced at DB level
2. **Check Constraints**: 
   - Quantities > 0
   - Prices >= 0
   - Dates logical (due_date > invoice_date)
3. **Unique Constraints**: 
   - Order numbers, quote numbers, invoice numbers
   - User emails, SKUs
4. **Cascade Rules**:
   - Delete order → delete order items
   - Delete quotation → delete quotation items
   - Delete invoice → delete invoice items

## Indexing Strategy

- Primary keys: Clustered indexes (UUID)
- Foreign keys: Non-clustered indexes
- Frequently queried fields: status, dates, numbers
- Search fields: names, descriptions (consider full-text search)

## Performance Considerations

1. **Partitioning**: Consider partitioning audit_logs by date
2. **Archiving**: Move completed orders older than 2 years to archive tables
3. **Materialized Views**: For complex dashboard queries
4. **Query Optimization**: Use EXPLAIN ANALYZE for slow queries
5. **Connection Pooling**: Configure appropriate pool size

## Backup & Recovery

- **Daily backups**: Full database backup
- **Point-in-time recovery**: WAL archiving enabled
- **Retention**: 30 days for daily, 12 months for monthly
- **Testing**: Monthly restore testing

## Migration Strategy

- Use Alembic for version-controlled migrations
- Test migrations on staging before production
- Maintain rollback scripts for each migration
- Document breaking changes
