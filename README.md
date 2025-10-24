# Medical Equipment Supply Enterprise Application

## 🎯 Overview

A unified enterprise application for managing end-to-end medical equipment supply operations serving hospitals. This system provides role-based access control, complete order lifecycle tracking, inventory management, and financial visibility.

## 🏗️ System Architecture

### Architecture Pattern
**Layered Monolith with Service-Oriented Design**

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  (Role-based UI, Dashboards, Forms, Notifications)      │
└─────────────────────────────────────────────────────────┘
                          ↓ REST API
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
├─────────────────────────────────────────────────────────┤
│  API Layer (Routes, Controllers, Auth Middleware)       │
├─────────────────────────────────────────────────────────┤
│  Service Layer (Business Logic, Workflow Orchestration) │
├─────────────────────────────────────────────────────────┤
│  Data Access Layer (SQLAlchemy ORM, Repositories)       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                         │
│  (Transactional Data, Audit Logs, Analytics)            │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **FastAPI** (Python 3.11+): High-performance async framework
- **SQLAlchemy 2.0**: ORM with relationship management
- **Alembic**: Database migrations
- **Pydantic**: Data validation and serialization
- **JWT**: Token-based authentication
- **Bcrypt**: Password hashing

**Frontend:**
- **React 18** with TypeScript
- **Vite**: Build tool and dev server
- **React Router**: Client-side routing
- **TanStack Query**: Server state management
- **Recharts**: Dashboard visualizations
- **Tailwind CSS**: Styling framework
- **shadcn/ui**: Component library
- **Lucide React**: Icon library

**Database:**
- **PostgreSQL 15+**: Primary database
- **Redis** (optional): Caching and session management

**DevOps:**
- **Docker & Docker Compose**: Containerization
- **GitHub Actions**: CI/CD pipeline
- **Pytest**: Backend testing
- **Jest & React Testing Library**: Frontend testing

## 👥 User Roles & Permissions

### 1. Executive
- **Responsibilities**: Approve orders, quotations, POs; full system visibility
- **Access**: All modules (Orders, Inventory, Accounts, Dashboards)
- **Permissions**: Read/Write on all entities, approval authority

### 2. Sales Representative
- **Responsibilities**: Create order requests from hospital inquiries
- **Access**: Order creation form, own order status tracking
- **Permissions**: Create orders, view own orders only

### 3. Decoder
- **Responsibilities**: Map order requests to inventory SKUs
- **Access**: Assigned orders, inventory catalog (read-only)
- **Permissions**: Update order items with SKU mapping, submit for approval

### 4. Quoter
- **Responsibilities**: Generate quotations and invoices
- **Access**: Approved decoded orders, quotation management
- **Permissions**: Create/edit quotations, generate invoices

### 5. Inventory Admin
- **Responsibilities**: Manage inventory, stock levels, dispatches
- **Access**: Full inventory module
- **Permissions**: CRUD on inventory items, update stock levels

## 🔄 Order Workflow

### Pre-Sales Phase
```
1. Order Request (Sales Rep)
   ↓
2. Decoding (Decoder assigns SKUs)
   ↓
3. Decoding Approval (Executive)
   ↓
4. Quotation Generation (Quoter)
   ↓
5. Quotation Approval (Executive)
   ↓
6. Quotation Sent to Customer
```

### Post-Sales Phase
```
7. PO Received from Hospital
   ↓
8. PO Approval (Executive)
   ↓
9. Inventory Check (Inventory Admin)
   ↓
10. Invoice Request (Quoter)
    ↓
11. Invoice Approval (Executive)
    ↓
12. Invoice Submission to Accounts
    ↓
13. Dispatch & Payment Tracking
```

## 📊 Database Schema

### Core Entities
- **Users**: Authentication and role management
- **Roles**: RBAC definitions
- **Customers**: Hospital/client information
- **Orders**: Order requests and lifecycle tracking
- **OrderItems**: Individual items in orders
- **Inventory**: Product catalog and stock levels
- **Quotations**: Price quotes with terms
- **QuotationItems**: Line items in quotations
- **Invoices**: Billing documents
- **Approvals**: Workflow approval tracking
- **AuditLogs**: Complete audit trail
- **Notifications**: In-app alerts

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose

### Installation

1. **Clone and navigate to project:**
```bash
cd "/Users/praneeth/Documents/PV enterprise 2"
```

2. **Backend Setup:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Database Setup:**
```bash
# Create PostgreSQL database
createdb medical_supply_db

# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py
```

4. **Frontend Setup:**
```bash
cd frontend
npm install
```

### Running the Application

**Development Mode:**

Terminal 1 - Backend:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

**Production Mode (Docker):**
```bash
docker-compose up -d
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Project Structure

```
medical-equipment-supply/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── orders.py
│   │   │   │   │   ├── inventory.py
│   │   │   │   │   ├── quotations.py
│   │   │   │   │   ├── invoices.py
│   │   │   │   │   └── dashboard.py
│   │   │   │   └── api.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── permissions.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── order.py
│   │   │   ├── inventory.py
│   │   │   ├── quotation.py
│   │   │   └── audit.py
│   │   ├── schemas/
│   │   │   └── (Pydantic models)
│   │   ├── services/
│   │   │   ├── order_service.py
│   │   │   ├── workflow_service.py
│   │   │   └── notification_service.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   ├── orders/
│   │   │   ├── inventory/
│   │   │   ├── dashboard/
│   │   │   └── common/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── types/
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci-cd.yml
└── README.md
```

## 🔒 Security Features

- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- Password hashing with bcrypt
- SQL injection prevention via ORM
- CORS configuration
- Rate limiting on API endpoints
- Audit logging for all critical operations
- Data encryption at rest and in transit

## 📈 Key Features

### For Executives
- Real-time dashboard with KPIs
- Order approval workflow
- Revenue and inventory analytics
- Outstanding invoices tracking
- Pending orders visibility

### For Sales Representatives
- Quick order creation form
- Order status tracking
- Customer management
- Order history

### For Decoders
- Order queue with pending items
- Inventory search and SKU mapping
- Bulk item decoding
- Approval submission

### For Quoters
- Quotation builder with pricing
- GST and discount calculations
- Invoice generation
- Template management

### For Inventory Admins
- Inventory CRUD operations
- Stock level management
- Dispatch tracking
- Low stock alerts

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
npm run test:coverage
```

## 🚢 Deployment

### Docker Deployment
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables
Create `.env` files for backend and frontend:

**Backend `.env`:**
```
DATABASE_URL=postgresql://user:password@localhost:5432/medical_supply_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Frontend `.env`:**
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## 📊 Analytics & Reporting

- Order volume trends
- Revenue by customer/period
- Inventory turnover rates
- Pending orders dashboard
- Outstanding invoices report
- Sales representative performance

## 🔄 Future Enhancements

- Multi-tenant support for regional expansion
- Mobile app for field sales
- WhatsApp/Email integration for order creation
- Advanced analytics with ML predictions
- Automated reorder points
- Supplier management module
- Payment gateway integration
- Document management system

## 📝 API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

This is an enterprise application. Contact the development team for contribution guidelines.

## 📄 License

Proprietary - All rights reserved

## 📞 Support

For technical support, contact the IT department.
