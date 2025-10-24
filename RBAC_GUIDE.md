# Role-Based Access Control (RBAC) Guide

## ✅ RBAC Now Implemented

The application now properly enforces role-based access control. Users will only see and access modules they have permission for.

## 🔒 How It Works

### 1. Navigation Menu Filtering
The sidebar navigation is dynamically filtered based on user permissions. Users only see menu items they can access.

### 2. Route Protection
Each route is protected with permission checks. If a user tries to access a URL directly without permission, they'll see an "Access Denied" message.

### 3. Permission Structure
Permissions are stored in the database and checked on both frontend and backend:
- **Frontend**: Controls UI visibility and route access
- **Backend**: Validates API requests (already implemented)

## 👥 Role Permissions

### Executive (Admin)
**Full System Access**
- ✅ Dashboard (analytics and metrics)
- ✅ Orders (view all, create, approve)
- ✅ Inventory (view, manage)
- ✅ Customers (view, manage)
- ✅ Quotations (view, approve)
- ✅ Invoices (view, approve)
- ✅ User Management
- ✅ All approval workflows

**Permissions:**
```json
{
  "dashboard:view": true,
  "order:read": true,
  "order:create": true,
  "order:update": true,
  "order:delete": true,
  "order:approve": true,
  "inventory:read": true,
  "inventory:create": true,
  "inventory:update": true,
  "inventory:delete": true,
  "customer:read": true,
  "customer:create": true,
  "customer:update": true,
  "customer:delete": true,
  "quotation:read": true,
  "quotation:approve": true,
  "invoice:read": true,
  "invoice:approve": true,
  "user:read": true,
  "user:create": true,
  "user:update": true
}
```

### Sales Representative
**Limited to Sales Functions**
- ✅ Dashboard (basic view)
- ✅ Orders (create and view own orders only)
- ✅ Customers (view and create)
- ❌ Inventory (no access)
- ❌ Quotations (no access)
- ❌ Invoices (no access)

**Permissions:**
```json
{
  "dashboard:view": true,
  "order:read": true,
  "order:create": true,
  "customer:read": true,
  "customer:create": true
}
```

### Decoder
**Order Processing Focus**
- ✅ Dashboard (basic view)
- ✅ Orders (view and decode)
- ✅ Inventory (read-only for mapping)
- ❌ Customers (no access)
- ❌ Quotations (no access)
- ❌ Invoices (no access)

**Permissions:**
```json
{
  "dashboard:view": true,
  "order:read": true,
  "order:update": true,
  "inventory:read": true
}
```

### Quoter
**Quotation and Invoice Management**
- ✅ Dashboard (basic view)
- ✅ Orders (read-only)
- ✅ Inventory (read-only for pricing)
- ✅ Customers (read-only)
- ✅ Quotations (create, update, delete)
- ✅ Invoices (create, update, delete)
- ❌ Inventory management (no access)

**Permissions:**
```json
{
  "dashboard:view": true,
  "order:read": true,
  "inventory:read": true,
  "customer:read": true,
  "quotation:read": true,
  "quotation:create": true,
  "quotation:update": true,
  "quotation:delete": true,
  "invoice:read": true,
  "invoice:create": true,
  "invoice:update": true,
  "invoice:delete": true
}
```

### Inventory Admin
**Stock and Dispatch Management**
- ✅ Dashboard (inventory-focused)
- ✅ Orders (read-only)
- ✅ Inventory (full CRUD access)
- ✅ Customers (read-only)
- ✅ Dispatches (create and manage)
- ❌ Quotations (no access)
- ❌ Invoices (no access)

**Permissions:**
```json
{
  "dashboard:view": true,
  "order:read": true,
  "inventory:read": true,
  "inventory:create": true,
  "inventory:update": true,
  "inventory:delete": true,
  "customer:read": true,
  "dispatch:read": true,
  "dispatch:create": true,
  "dispatch:update": true
}
```

## 🧪 Testing RBAC

### Test Each Role

1. **Login as Sales Rep** (`sales@medicalequipment.com` / `sales123`)
   - Should see: Dashboard, Orders, Customers
   - Should NOT see: Inventory
   - Try accessing `/inventory` directly - should see "Access Denied"

2. **Login as Decoder** (`decoder@medicalequipment.com` / `decoder123`)
   - Should see: Dashboard, Orders, Inventory
   - Should NOT see: Customers
   - Inventory should be read-only

3. **Login as Quoter** (`quoter@medicalequipment.com` / `quoter123`)
   - Should see: Dashboard, Orders, Inventory, Customers
   - All except Dashboard should be read-only or for quotation purposes

4. **Login as Inventory Admin** (`inventory@medicalequipment.com` / `inventory123`)
   - Should see: Dashboard, Orders, Inventory, Customers
   - Full access to Inventory management

5. **Login as Executive** (`admin@medicalequipment.com` / `admin123`)
   - Should see: All modules
   - Full access to everything

## 🔐 Security Layers

### Frontend Protection
1. **Navigation Filtering**: Menu items filtered by permissions
2. **Route Guards**: `PermissionRoute` component checks permissions
3. **UI Element Hiding**: Buttons/actions hidden based on permissions

### Backend Protection (Already Implemented)
1. **JWT Authentication**: All requests require valid token
2. **Permission Decorators**: `PermissionChecker` validates permissions
3. **Database Queries**: Filtered by user role and ownership

## 📝 Implementation Details

### Frontend Changes Made

**1. Layout.tsx**
- Added permission-based navigation filtering
- Navigation items now include `permission` field
- Menu dynamically shows only allowed items

**2. App.tsx**
- Added `PermissionRoute` component
- Wrapped all routes with permission checks
- Shows "Access Denied" for unauthorized access

### How to Add New Protected Routes

```tsx
<Route 
  path="new-module" 
  element={
    <PermissionRoute permission="module:read">
      <NewModulePage />
    </PermissionRoute>
  } 
/>
```

### How to Add New Navigation Items

```tsx
{ 
  name: 'New Module', 
  href: '/new-module', 
  icon: IconComponent,
  permission: 'module:read'
}
```

## 🎯 Best Practices

1. **Always Check Permissions**: Both frontend and backend
2. **Fail Securely**: Deny access by default
3. **Log Access Attempts**: Backend logs all permission checks
4. **Regular Audits**: Review audit logs for unauthorized attempts
5. **Principle of Least Privilege**: Give users minimum required permissions

## 🔄 Updating Permissions

To modify role permissions, update the seed data in:
`backend/scripts/seed_data.py`

Then re-run:
```bash
python scripts/seed_data.py
```

Or update directly in database:
```sql
UPDATE roles 
SET permissions = '{"permission:name": true}'::jsonb 
WHERE name = 'role_name';
```

## ✅ Verification Checklist

- [x] Navigation menu filters by role
- [x] Direct URL access blocked without permission
- [x] Backend API validates permissions
- [x] Audit logs track access attempts
- [x] Each role has appropriate access level
- [x] Users can only see their authorized data

## 🚀 Next Steps

The RBAC system is now fully functional. Users will only see and access what they're authorized for. Test with different user accounts to verify the access control is working correctly.

**Remember**: Always logout and login again after making permission changes to see the updated access rights!
