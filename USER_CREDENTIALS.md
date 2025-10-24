# User Credentials - Demo Accounts

## 🔐 All Demo User Accounts

All users are already seeded in the database and ready to use!

---

## 1. 👔 Executive (Admin)

**Email**: `admin@medicalequipment.com`  
**Password**: `admin123`  
**Full Name**: Admin User  
**Role**: executive

**Access Level**: Full system access

---

## 2. 💼 Sales Representative

**Email**: `sales@medicalequipment.com`  
**Password**: `sales123`  
**Full Name**: John Sales  
**Role**: sales_rep

**Access Level**: Orders and Customers (limited)

---

## 3. 🔍 Decoder

**Email**: `decoder@medicalequipment.com`  
**Password**: `decoder123`  
**Full Name**: Jane Decoder  
**Role**: decoder

**Access Level**: Order processing and inventory viewing

---

## 4. 📋 Quoter

**Email**: `quoter@medicalequipment.com`  
**Password**: `quoter123`  
**Full Name**: Mike Quoter  
**Role**: quoter

**Access Level**: Quotations and invoices

---

## 5. 📦 Inventory Admin ⭐

**Email**: `inventory@medicalequipment.com`  
**Password**: `inventory123`  
**Full Name**: Sarah Inventory  
**Role**: inventory_admin

**Access Level**: Full inventory control and dispatch management

---

## 🧪 Quick Test Guide

### Test Inventory Admin

1. **Login**:
   ```
   Email: inventory@medicalequipment.com
   Password: inventory123
   ```

2. **You should see**:
   - Dashboard
   - Orders (read-only)
   - Inventory (full access)
   - Customers (read-only)

3. **You should NOT see**:
   - Quotations
   - Invoices
   - User Management

4. **Test Inventory Access**:
   - Go to Inventory page
   - ✅ See "Add Item" button
   - ✅ Click it - should show alert
   - ✅ Can view all inventory items
   - ✅ Can edit inventory items (when implemented)
   - ✅ Can delete inventory items (when implemented)

---

## 📊 Quick Reference Table

| User | Email | Password | Role | Can Add Inventory |
|------|-------|----------|------|-------------------|
| Admin | admin@medicalequipment.com | admin123 | Executive | ✅ |
| Sales | sales@medicalequipment.com | sales123 | Sales Rep | ❌ |
| Decoder | decoder@medicalequipment.com | decoder123 | Decoder | ❌ |
| Quoter | quoter@medicalequipment.com | quoter123 | Quoter | ❌ |
| **Inventory** | **inventory@medicalequipment.com** | **inventory123** | **Inventory Admin** | **✅** |

---

## 🔄 Database Status

✅ **All users are already in the database!**

Created on: October 23, 2025 at 8:55 PM  
Database: `medical_supply_db`  
Total Users: 5

---

## 🔒 Security Notes

### For Production:

⚠️ **IMPORTANT**: These are demo credentials for development only!

Before deploying to production:

1. **Change all passwords** to strong, unique passwords
2. **Remove demo accounts** or disable them
3. **Create real user accounts** with proper credentials
4. **Enable password complexity requirements**
5. **Implement password expiry policies**
6. **Add two-factor authentication (2FA)**
7. **Set up password reset functionality**

### Current Security:

- ✅ Passwords are hashed with bcrypt
- ✅ JWT tokens for authentication
- ✅ Role-based access control (RBAC)
- ✅ Permission checks on all endpoints
- ✅ Audit logging enabled

---

## 🚀 Login Instructions

1. **Open the application**: http://localhost:3000
2. **Enter credentials** from the table above
3. **Click "Login"**
4. **Explore** the features available to that role

---

## 📝 Need More Users?

To add more users, you can:

### Option 1: Use the Admin Account
1. Login as admin
2. Go to User Management (when implemented)
3. Create new users with appropriate roles

### Option 2: Run Seed Script Again
```bash
cd backend
source venv/bin/activate
python scripts/seed_data.py
```

### Option 3: Add Manually via Database
```sql
INSERT INTO users (email, hashed_password, full_name, role_id, is_active)
VALUES ('newuser@example.com', 'hashed_password', 'New User', 'role_id', true);
```

---

## ✅ Verification

All 5 users are confirmed in the database:

- ✅ admin@medicalequipment.com (Executive)
- ✅ sales@medicalequipment.com (Sales Rep)
- ✅ decoder@medicalequipment.com (Decoder)
- ✅ quoter@medicalequipment.com (Quoter)
- ✅ **inventory@medicalequipment.com (Inventory Admin)** ⭐

**Ready to use!** Just login with any of the credentials above.
