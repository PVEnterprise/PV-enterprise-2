# System Architecture Documentation

## Overview

The Medical Equipment Supply System is a full-stack enterprise application built with a modern, scalable architecture. It follows a layered monolith pattern with service-oriented design principles.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  React 18 + TypeScript Frontend                      │   │
│  │  - TanStack Query (Server State)                     │   │
│  │  - React Router (Navigation)                         │   │
│  │  - Tailwind CSS (Styling)                            │   │
│  │  - Recharts (Visualizations)                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                 │   │
│  │  - CORS Middleware                                   │   │
│  │  - JWT Authentication                                │   │
│  │  - Request Validation (Pydantic)                     │   │
│  │  - OpenAPI Documentation                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Endpoints (Controllers)                         │   │
│  │  - Auth, Orders, Inventory, Customers, etc.         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Service Layer (Business Logic)                      │   │
│  │  - Order Workflow Management                         │   │
│  │  - Approval Orchestration                            │   │
│  │  - Notification Service                              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Security & Authorization                            │   │
│  │  - Role-Based Access Control (RBAC)                 │   │
│  │  - Permission Checking                               │   │
│  │  - JWT Token Management                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Data Access Layer                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SQLAlchemy ORM                                      │   │
│  │  - Models (Entities)                                 │   │
│  │  - Relationships                                     │   │
│  │  - Query Building                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Persistence Layer                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PostgreSQL Database                                 │   │
│  │  - Transactional Data                                │   │
│  │  - Audit Logs                                        │   │
│  │  - Full-Text Search                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **State Management**: 
  - TanStack Query (Server state)
  - React Context (Auth state)
- **Styling**: Tailwind CSS
- **UI Components**: Custom components with shadcn/ui patterns
- **Icons**: Lucide React
- **Charts**: Recharts
- **HTTP Client**: Axios

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: JWT (python-jose)
- **Password Hashing**: Bcrypt (passlib)
- **API Documentation**: OpenAPI/Swagger

### Database
- **Primary Database**: PostgreSQL 15+
- **Features Used**:
  - JSONB for flexible data
  - UUID primary keys
  - Computed columns
  - Check constraints
  - Indexes for performance

### DevOps
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions (ready)
- **Testing**: Pytest (backend), Vitest (frontend)

## Design Patterns

### 1. Repository Pattern
Data access is abstracted through SQLAlchemy ORM, providing a clean separation between business logic and data persistence.

### 2. Dependency Injection
FastAPI's dependency injection system is used for:
- Database session management
- Authentication
- Authorization checks

### 3. Factory Pattern
Used for generating unique identifiers (order numbers, quote numbers, invoice numbers).

### 4. Strategy Pattern
Role-based permissions allow different behaviors based on user roles.

### 5. Observer Pattern
Audit logging observes all critical operations and records changes.

## Security Architecture

### Authentication Flow
```
1. User submits credentials
2. Backend validates credentials
3. Generate JWT access token (30 min expiry)
4. Generate JWT refresh token (7 days expiry)
5. Return both tokens to client
6. Client stores tokens in localStorage
7. Client includes access token in Authorization header
8. Backend validates token on each request
9. On token expiry, use refresh token to get new access token
```

### Authorization (RBAC)
```
User → Role → Permissions → Resources

Roles:
- Executive: Full access, approval authority
- Sales Rep: Create orders, view own orders
- Decoder: Decode orders, view inventory
- Quoter: Create quotations/invoices
- Inventory Admin: Manage inventory, dispatches

Permissions are checked at:
1. API endpoint level (route dependencies)
2. Business logic level (service methods)
3. Data access level (query filters)
```

### Security Features
- Password hashing with bcrypt (cost factor 12)
- JWT tokens with expiration
- CORS configuration
- SQL injection prevention (ORM)
- Input validation (Pydantic)
- Rate limiting (ready for implementation)
- Audit logging for compliance

## Data Flow

### Order Creation Flow
```
1. Sales Rep creates order via frontend
2. Frontend sends POST /api/v1/orders/
3. Backend validates user permissions
4. Backend validates customer exists
5. Generate unique order number
6. Create order and order items in database
7. Return order details to frontend
8. Frontend updates UI and cache
```

### Order Workflow State Machine
```
order_request → decoding → decoding_approval → quotation → 
quotation_approval → quotation_sent → po_received → po_approval → 
inventory_check → invoice_request → invoice_approval → invoiced → 
dispatched → completed

At each stage:
- Status checks prevent invalid transitions
- Approval records track who approved/rejected
- Audit logs record all changes
- Notifications alert relevant users
```

## Database Schema Highlights

### Key Entities
- **Users & Roles**: Authentication and authorization
- **Customers**: Hospital/client information
- **Orders & OrderItems**: Order lifecycle tracking
- **Inventory**: Product catalog and stock
- **Quotations & QuotationItems**: Price quotes
- **Invoices & InvoiceItems**: Billing documents
- **Approvals**: Workflow approval tracking
- **AuditLogs**: Complete audit trail
- **Notifications**: User notifications
- **Dispatches**: Shipment tracking

### Relationships
- One-to-Many: Order → OrderItems, Customer → Orders
- Many-to-One: Order → Customer, OrderItem → Inventory
- Polymorphic: Approvals → Multiple entities

### Indexing Strategy
- Primary keys: UUID with index
- Foreign keys: Indexed for joins
- Status fields: Indexed for filtering
- Search fields: Consider full-text search indexes
- Dates: Indexed for range queries

## API Design

### RESTful Principles
- Resource-based URLs
- HTTP methods for CRUD operations
- Proper status codes
- Consistent response format
- Pagination for lists
- Filtering and search support

### Endpoint Structure
```
/api/v1/
  /auth/
    POST /login
    POST /refresh
    GET /me
  /orders/
    GET / (list)
    POST / (create)
    GET /{id} (detail)
    PUT /{id} (update)
    POST /{id}/approve
    POST /{id}/reject
  /inventory/
    GET / (list)
    POST / (create)
    GET /{id} (detail)
    PUT /{id} (update)
    POST /{id}/stock (update stock)
  /customers/
  /quotations/
  /invoices/
  /dashboard/
```

### Response Format
```json
{
  "id": "uuid",
  "field": "value",
  "created_at": "2025-01-23T12:00:00Z",
  "updated_at": "2025-01-23T12:00:00Z"
}
```

### Error Format
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

## Scalability Considerations

### Current Architecture
- Layered monolith suitable for small to medium scale
- Single database instance
- Stateless API (horizontal scaling ready)

### Future Enhancements
1. **Caching Layer**: Redis for frequently accessed data
2. **Message Queue**: RabbitMQ/Celery for async tasks
3. **Microservices**: Split into order, inventory, billing services
4. **Read Replicas**: For reporting and analytics
5. **CDN**: For static assets
6. **Load Balancer**: Distribute traffic across API instances
7. **Multi-tenancy**: Support multiple organizations

## Performance Optimization

### Database
- Connection pooling (configured)
- Prepared statements (ORM)
- Eager loading for relationships
- Pagination for large datasets
- Indexes on frequently queried fields

### API
- Response caching (ready for Redis)
- Compression middleware
- Async endpoints where beneficial
- Query optimization

### Frontend
- Code splitting
- Lazy loading routes
- React Query caching
- Debounced search inputs
- Optimistic updates

## Monitoring & Observability

### Logging
- Application logs (FastAPI)
- Database query logs (SQLAlchemy)
- Audit logs (custom)
- Error tracking (ready for Sentry)

### Metrics (Ready for Implementation)
- Request rate
- Response time
- Error rate
- Database query performance
- Active users

### Health Checks
- `/health` endpoint
- Database connectivity check
- Service dependencies check

## Testing Strategy

### Backend Testing
- Unit tests for business logic
- Integration tests for API endpoints
- Database tests with test fixtures
- Authentication/authorization tests

### Frontend Testing
- Component tests
- Integration tests
- E2E tests (ready for Playwright)

### Test Coverage Goals
- Backend: >80%
- Frontend: >70%
- Critical paths: 100%

## Deployment Architecture

### Development
```
Local Machine
├── Backend (localhost:8000)
├── Frontend (localhost:3000)
└── PostgreSQL (localhost:5432)
```

### Production (Recommended)
```
Load Balancer
├── Frontend Instances (Nginx/CDN)
├── Backend Instances (Gunicorn/Uvicorn)
└── PostgreSQL (Managed Service)
```

## Compliance & Audit

### Audit Trail
Every critical operation is logged:
- Who performed the action
- What was changed (old vs new values)
- When it occurred
- IP address and user agent

### Data Retention
- Active data: Indefinite
- Audit logs: 7 years (configurable)
- Archived orders: 2 years in main DB, then archive

### GDPR Considerations
- User data export capability
- Data deletion on request
- Consent tracking (ready for implementation)

## Future Roadmap

### Phase 2 Features
- Mobile app (React Native)
- WhatsApp/Email integration
- Advanced analytics with ML
- Automated reorder points
- Supplier management
- Payment gateway integration
- Document management (PDF generation)

### Phase 3 Features
- Multi-tenant support
- Regional expansion
- Advanced reporting
- BI dashboard
- API for third-party integrations
- Mobile-first progressive web app

## Conclusion

This architecture provides:
- ✅ Scalability through stateless design
- ✅ Security through RBAC and JWT
- ✅ Maintainability through clean separation of concerns
- ✅ Testability through dependency injection
- ✅ Extensibility through modular design
- ✅ Performance through caching and optimization
- ✅ Reliability through error handling and logging
