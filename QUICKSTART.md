# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker Desktop installed and running
- Terminal/Command Prompt

### Step 1: Navigate to Project
```bash
cd "/Users/praneeth/Documents/PV enterprise 2"
```

### Step 2: Create Environment Files
```bash
# Backend environment
cp backend/.env.example backend/.env

# Frontend environment
cp frontend/.env.example frontend/.env
```

### Step 3: Start All Services
```bash
docker-compose up -d
```

This will start:
- ✅ PostgreSQL database (port 5432)
- ✅ Backend API (port 8000)
- ✅ Frontend app (port 3000)

### Step 4: Initialize Database (Wait 10 seconds for services to start)
```bash
# Create database tables
docker-compose exec backend alembic upgrade head

# Seed initial data (roles and demo users)
docker-compose exec backend python scripts/seed_data.py
```

### Step 5: Access the Application

**Frontend Application:**
```
http://localhost:3000
```

**Backend API Documentation:**
```
http://localhost:8000/docs
```

### Step 6: Login with Demo Credentials

**Executive (Full Access):**
- Email: `admin@medicalequipment.com`
- Password: `admin123`

**Sales Representative:**
- Email: `sales@medicalequipment.com`
- Password: `sales123`

**Decoder:**
- Email: `decoder@medicalequipment.com`
- Password: `decoder123`

**Quoter:**
- Email: `quoter@medicalequipment.com`
- Password: `quoter123`

**Inventory Admin:**
- Email: `inventory@medicalequipment.com`
- Password: `inventory123`

---

## 🎯 Test the Complete Workflow

### 1. Login as Sales Rep
```
Email: sales@medicalequipment.com
Password: sales123
```
- Create a new customer
- Create an order with items

### 2. Login as Decoder
```
Email: decoder@medicalequipment.com
Password: decoder123
```
- View pending orders
- Decode items (map to inventory SKUs)
- Submit for approval

### 3. Login as Executive
```
Email: admin@medicalequipment.com
Password: admin123
```
- View pending approvals
- Approve decoded order
- View dashboard analytics

### 4. Login as Quoter
```
Email: quoter@medicalequipment.com
Password: quoter123
```
- Create quotation from approved order
- Submit for approval

### 5. Login as Executive (Again)
```
Email: admin@medicalequipment.com
Password: admin123
```
- Approve quotation
- View complete order lifecycle

---

## 🛠️ Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Access Database
```bash
docker-compose exec postgres psql -U postgres -d medical_supply_db
```

### Run Backend Commands
```bash
# Access backend shell
docker-compose exec backend bash

# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"
```

---

## 🐛 Troubleshooting

### Services Won't Start
```bash
# Check if ports are in use
lsof -i :3000
lsof -i :8000
lsof -i :5432

# Stop conflicting processes
docker-compose down
docker system prune -a
docker-compose up -d
```

### Database Connection Error
```bash
# Wait for database to be ready
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Frontend Not Loading
```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

### Backend API Errors
```bash
# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend

# Check database connection
docker-compose exec backend python -c "from app.db.session import engine; print(engine.connect())"
```

---

## 📚 Next Steps

1. ✅ **Explore the Dashboard** - View real-time statistics
2. ✅ **Create Test Data** - Add customers, inventory, orders
3. ✅ **Test Workflows** - Complete order lifecycle
4. ✅ **Review API Docs** - http://localhost:8000/docs
5. ✅ **Read Documentation** - Check README.md and SETUP_GUIDE.md

---

## 🔒 Security Notes

⚠️ **IMPORTANT**: The demo credentials are for testing only!

Before production deployment:
1. Change all default passwords
2. Generate a strong SECRET_KEY
3. Configure proper CORS origins
4. Enable HTTPS
5. Set up proper database credentials
6. Review security checklist in SETUP_GUIDE.md

---

## 📞 Need Help?

- **Documentation**: Check README.md and SETUP_GUIDE.md
- **API Reference**: http://localhost:8000/docs
- **Architecture**: See ARCHITECTURE.md
- **Database Schema**: See DATABASE_SCHEMA.md

---

## ✨ Features to Try

### As Executive
- View dashboard with analytics
- Approve/reject orders
- Approve quotations
- View all system data

### As Sales Rep
- Create customers
- Create orders
- View own orders
- Track order status

### As Decoder
- View pending orders
- Map items to inventory
- Submit for approval

### As Quoter
- Create quotations
- Generate invoices
- Track payments

### As Inventory Admin
- Manage inventory items
- Update stock levels
- Create dispatches
- View low stock alerts

---

**Enjoy exploring the Medical Equipment Supply System! 🎉**
