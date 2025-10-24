# Complete Roles & Permissions Overview

## 🎭 All User Roles

The system has **5 distinct roles**, each with specific permissions tailored to their responsibilities.

---

## 1. 👔 Executive (Admin)

**Description**: Executive with full system access and approval authority

**Login**: `admin@medicalequipment.com` / `admin123`

### Full Permissions:
- ✅ **Orders**: Create, Read All, Update, Delete, Approve
- ✅ **Inventory**: Create, Read, Update, Delete
- ✅ **Customers**: Create, Read, Update, Delete
- ✅ **Quotations**: Create, Read, Update, Delete, Approve
- ✅ **Invoices**: Create, Read, Update, Delete, Approve
- ✅ **Users**: Create, Read, Update, Delete
- ✅ **Dispatches**: Create, Read, Update
- ✅ **Dashboard**: View, Analytics
- ✅ **Approvals**: Execute all approval workflows

### What They Can Do:
- Manage the entire system
- Approve orders, quotations, and invoices
- Create and manage users
- View all data and analytics
- Override any decision
- Full CRUD on all modules

---

## 2. 💼 Sales Representative

**Description**: Sales representative who creates order requests

**Login**: `sales@medicalequipment.com` / `sales123`

### Permissions:
- ✅ **Orders**: Create, Read (own orders only)
- ✅ **Customers**: Read only
- ✅ **Dashboard**: Basic view
- ❌ **No access to**: Inventory, Quotations, Invoices, User Management

### What They Can Do:
- Create new order requests
- View their own orders
- View customer list (read-only)
- See basic dashboard metrics
- Track order status

### What They CANNOT Do:
- ❌ Create or edit customers
- ❌ Access inventory
- ❌ Create quotations or invoices
- ❌ Approve anything
- ❌ See other sales reps' orders

---

## 3. 🔍 Decoder

**Description**: Decoder who maps order items to inventory SKUs

**Login**: `decoder@medicalequipment.com` / `decoder123`

### Permissions:
- ✅ **Orders**: Read, Update (decoding only)
- ✅ **Inventory**: Read only
- ✅ **Customers**: Read only
- ✅ **Dashboard**: Basic view
- ❌ **No access to**: Quotations, Invoices, User Management

### What They Can Do:
- View orders assigned for decoding
- Map order items to inventory SKUs
- Update order items with inventory details
- View inventory catalog (read-only)
- View customer information
- Submit decoded orders for approval

### What They CANNOT Do:
- ❌ Create orders
- ❌ Create or edit customers
- ❌ Modify inventory
- ❌ Create quotations or invoices
- ❌ Approve anything

---

## 4. 📋 Quoter

**Description**: Quoter who generates quotations and invoices

**Login**: `quoter@medicalequipment.com` / `quoter123`

### Permissions:
- ✅ **Orders**: Read only
- ✅ **Quotations**: Create, Read, Update, Delete
- ✅ **Invoices**: Create, Read, Update, Delete
- ✅ **Inventory**: Read only (for pricing)
- ✅ **Customers**: Read only
- ✅ **Dashboard**: Basic view
- ❌ **No access to**: User Management, Approvals

### What They Can Do:
- View approved orders
- Create quotations from orders
- Manage quotation details
- Create invoices from quotations
- Record payments
- View inventory for pricing
- View customer information
- Submit quotations/invoices for approval

### What They CANNOT Do:
- ❌ Create or edit orders
- ❌ Create or edit customers
- ❌ Modify inventory
- ❌ Approve quotations or invoices
- ❌ Manage dispatches

---

## 5. 📦 Inventory Admin

**Description**: Inventory administrator who manages stock and dispatches

**Login**: `inventory@medicalequipment.com` / `inventory123`

### Permissions:
- ✅ **Inventory**: **FULL ACCESS** (Create, Read, Update, Delete)
- ✅ **Orders**: Read only
- ✅ **Dispatches**: Create, Read, Update
- ✅ **Customers**: Read only
- ✅ **Dashboard**: Basic view
- ❌ **No access to**: Quotations, Invoices, User Management

### What They Can Do:
- **Full inventory management**:
  - ✅ Add new inventory items
  - ✅ Update item details
  - ✅ Update stock quantities
  - ✅ Delete inventory items
  - ✅ Set reorder levels
  - ✅ Manage categories
- Create and manage dispatches
- View orders to fulfill
- Track stock levels
- View low stock alerts
- View customer information

### What They CANNOT Do:
- ❌ Create or edit orders
- ❌ Create or edit customers
- ❌ Create quotations or invoices
- ❌ Approve anything

---

## 📊 Permission Comparison Table

| Permission | Executive | Sales Rep | Decoder | Quoter | Inventory Admin |
|------------|-----------|-----------|---------|--------|-----------------|
| **Orders** |
| Create | ✅ | ✅ | ❌ | ❌ | ❌ |
| Read | ✅ All | ✅ Own | ✅ | ✅ | ✅ |
| Update | ✅ | ❌ | ✅ Decode | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| Approve | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Inventory** |
| Create | ✅ | ❌ | ❌ | ❌ | ✅ |
| Read | ✅ | ❌ | ✅ | ✅ | ✅ |
| Update | ✅ | ❌ | ❌ | ❌ | ✅ |
| Delete | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Customers** |
| Create | ✅ | ❌ | ❌ | ❌ | ❌ |
| Read | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Quotations** |
| Create | ✅ | ❌ | ❌ | ✅ | ❌ |
| Read | ✅ | ❌ | ❌ | ✅ | ❌ |
| Update | ✅ | ❌ | ❌ | ✅ | ❌ |
| Delete | ✅ | ❌ | ❌ | ✅ | ❌ |
| Approve | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Invoices** |
| Create | ✅ | ❌ | ❌ | ✅ | ❌ |
| Read | ✅ | ❌ | ❌ | ✅ | ❌ |
| Update | ✅ | ❌ | ❌ | ✅ | ❌ |
| Delete | ✅ | ❌ | ❌ | ✅ | ❌ |
| Approve | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Dispatches** |
| Create | ✅ | ❌ | ❌ | ❌ | ✅ |
| Read | ✅ | ❌ | ❌ | ❌ | ✅ |
| Update | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Dashboard** | ✅ Analytics | ✅ Basic | ✅ Basic | ✅ Basic | ✅ Basic |
| **User Management** | ✅ Full | ❌ | ❌ | ❌ | ❌ |

---

## 🎯 Role Selection Guide

### When to use each role:

**Executive (Admin)**
- Company executives
- System administrators
- People who need full oversight
- Approval authority required

**Sales Representative**
- Field sales team
- Customer-facing staff
- Order creators
- Limited to their own data

**Decoder**
- Technical staff
- Product specialists
- SKU mapping experts
- Order processing team

**Quoter**
- Finance team
- Billing department
- Quote generation staff
- Invoice management

**Inventory Admin** ⭐
- Warehouse managers
- Stock controllers
- Logistics team
- Dispatch coordinators
- **Full control over inventory**

---

## 🔐 Security Features

### Role Enforcement
- ✅ Backend API validates all permissions
- ✅ Frontend hides unauthorized UI elements
- ✅ Database queries filter by role
- ✅ Audit logs track all actions

### Permission Checks
- ✅ Every API endpoint checks permissions
- ✅ Navigation menu filters by role
- ✅ Buttons show/hide based on permissions
- ✅ Routes protected with permission guards

---

## 📝 Important Notes

### Inventory Admin Highlights ⭐

The **Inventory Admin** role is specifically designed for warehouse and logistics operations:

1. **Full Inventory Control**
   - Can add new products to the system
   - Can update product details and pricing
   - Can adjust stock quantities
   - Can delete obsolete items
   - Can set reorder levels

2. **Dispatch Management**
   - Create dispatch records
   - Track shipments
   - Update delivery status
   - Link dispatches to orders

3. **Read-Only Access**
   - Can view orders (to know what to fulfill)
   - Can view customers (for shipping details)
   - Cannot modify orders or customers

4. **Dashboard Access**
   - View inventory metrics
   - See low stock alerts
   - Track dispatch status
   - Monitor fulfillment

### Why Separate Inventory Admin?

- **Specialization**: Dedicated role for warehouse operations
- **Security**: Prevents sales/quoter from modifying stock
- **Accountability**: Clear ownership of inventory data
- **Efficiency**: Focused permissions for the job

---

## 🧪 Testing All Roles

### Quick Test Script

1. **Login as each role**
2. **Check navigation menu** - should see only allowed modules
3. **Try accessing restricted URLs** - should see "Access Denied"
4. **Check button visibility** - should see only allowed actions
5. **Test API calls** - should get 403 for unauthorized actions

### Expected Results

| Role | Sees in Menu | Can Add Customer | Can Add Order | Can Add Inventory |
|------|--------------|------------------|---------------|-------------------|
| Executive | All | ✅ | ✅ | ✅ |
| Sales Rep | Dashboard, Orders, Customers | ❌ | ✅ | ❌ |
| Decoder | Dashboard, Orders, Inventory | ❌ | ❌ | ❌ |
| Quoter | Dashboard, Orders, Inventory, Customers | ❌ | ❌ | ❌ |
| Inventory Admin | Dashboard, Orders, Inventory, Customers | ❌ | ❌ | ✅ |

---

## ✅ Summary

**5 Roles Implemented:**
1. ✅ Executive - Full system access
2. ✅ Sales Representative - Order creation
3. ✅ Decoder - Order processing
4. ✅ Quoter - Quotation & invoice management
5. ✅ **Inventory Admin - Full inventory control** ⭐

**Inventory Admin has complete control over:**
- ✅ Adding inventory items
- ✅ Updating inventory items
- ✅ Deleting inventory items
- ✅ Managing stock levels
- ✅ Creating dispatches
- ✅ Tracking shipments

**All roles are properly configured and enforced at both frontend and backend levels!**
