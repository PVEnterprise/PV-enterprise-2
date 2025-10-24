# Setup Guide - Medical Equipment Supply System

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15+**
- **Docker & Docker Compose** (optional, for containerized deployment)

## Quick Start with Docker (Recommended)

### 1. Clone and Navigate to Project
```bash
cd "/Users/praneeth/Documents/PV enterprise 2"
```

### 2. Create Environment Files

**Backend `.env`:**
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your configuration:
```env
DATABASE_URL=postgresql://postgres:password@postgres:5432/medical_supply_db
SECRET_KEY=your-secret-key-here-generate-with-openssl-rand-hex-32
ALLOWED_ORIGINS=http://localhost:3000
```

**Frontend `.env`:**
```bash
cp frontend/.env.example frontend/.env
```

### 3. Start All Services
```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- Backend API on port 8000
- Frontend on port 3000

### 4. Initialize Database
```bash
# Wait for services to be healthy (about 10 seconds)
sleep 10

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed initial data (roles and users)
docker-compose exec backend python scripts/seed_data.py
```

### 5. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Backend ReDoc**: http://localhost:8000/redoc

### Default Login Credentials
- **Admin**: admin@medicalequipment.com / admin123
- **Sales Rep**: sales@medicalequipment.com / sales123
- **Decoder**: decoder@medicalequipment.com / decoder123
- **Quoter**: quoter@medicalequipment.com / quoter123
- **Inventory Admin**: inventory@medicalequipment.com / inventory123

⚠️ **IMPORTANT**: Change these passwords immediately in production!

---

## Manual Setup (Without Docker)

### Backend Setup

#### 1. Create Virtual Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Setup PostgreSQL Database
```bash
# Create database
createdb medical_supply_db

# Or using psql
psql -U postgres
CREATE DATABASE medical_supply_db;
\q
```

#### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your database credentials
```

#### 5. Run Migrations
```bash
alembic upgrade head
```

#### 6. Seed Initial Data
```bash
python scripts/seed_data.py
```

#### 7. Start Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000

### Frontend Setup

#### 1. Install Dependencies
```bash
cd frontend
npm install
```

#### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env if needed (default should work)
```

#### 3. Start Development Server
```bash
npm run dev
```

Frontend will be available at http://localhost:3000

---

## Database Migrations

### Create a New Migration
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

### View Migration History
```bash
alembic history
```

---

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## Production Deployment

### 1. Update Environment Variables
```env
# Backend .env
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=<generate-strong-secret-key>
DATABASE_URL=<production-database-url>
ALLOWED_ORIGINS=https://yourdomain.com
```

### 2. Build Production Images
```bash
docker-compose -f docker-compose.prod.yml build
```

### 3. Deploy
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Run Migrations
```bash
docker-compose exec backend alembic upgrade head
```

---

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U postgres -d medical_supply_db
```

### Backend Issues
```bash
# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend

# Access backend shell
docker-compose exec backend bash
```

### Frontend Issues
```bash
# View frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend

# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Port Conflicts
If ports 3000, 8000, or 5432 are already in use:
```bash
# Stop conflicting services
lsof -ti:8000 | xargs kill -9  # Kill process on port 8000

# Or change ports in docker-compose.yml
```

---

## API Documentation

### Interactive API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

#### Orders
- `GET /api/v1/orders/` - List orders
- `POST /api/v1/orders/` - Create order
- `GET /api/v1/orders/{id}` - Get order details
- `POST /api/v1/orders/{id}/items/{item_id}/decode` - Decode order item
- `POST /api/v1/orders/{id}/approve` - Approve order

#### Inventory
- `GET /api/v1/inventory/` - List inventory
- `POST /api/v1/inventory/` - Create inventory item
- `PUT /api/v1/inventory/{id}` - Update inventory item
- `POST /api/v1/inventory/{id}/stock` - Update stock

#### Customers
- `GET /api/v1/customers/` - List customers
- `POST /api/v1/customers/` - Create customer

#### Dashboard
- `GET /api/v1/dashboard/stats` - Get dashboard statistics

---

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Update models in `backend/app/models/`
- Create migration: `alembic revision --autogenerate -m "Add new field"`
- Update API endpoints in `backend/app/api/v1/endpoints/`
- Update frontend components in `frontend/src/`

### 3. Test Changes
```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test
```

### 4. Commit and Push
```bash
git add .
git commit -m "Add feature: description"
git push origin feature/your-feature-name
```

---

## Monitoring and Logs

### View All Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Access Database
```bash
docker-compose exec postgres psql -U postgres -d medical_supply_db
```

---

## Backup and Restore

### Backup Database
```bash
docker-compose exec postgres pg_dump -U postgres medical_supply_db > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
docker-compose exec -T postgres psql -U postgres medical_supply_db < backup_20250123.sql
```

---

## Performance Optimization

### Backend
- Enable Redis caching for frequently accessed data
- Use database connection pooling (already configured)
- Add indexes for frequently queried fields
- Implement pagination for large datasets

### Frontend
- Use React Query for efficient data caching
- Implement lazy loading for routes
- Optimize bundle size with code splitting
- Use production build for deployment

---

## Security Checklist

- [ ] Change default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS in production
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable database backups
- [ ] Implement audit logging
- [ ] Regular security updates

---

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at http://localhost:8000/docs
3. Check application logs
4. Contact the development team

---

## Next Steps

After successful setup:
1. Change default passwords
2. Create your first customer
3. Create an order
4. Test the complete workflow
5. Explore the dashboard
6. Review role-based access controls
