"""
API v1 router that includes all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, orders, inventory, customers, quotations, invoices, dashboard, users, attachments, dispatches, outstanding


api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(quotations.router, prefix="/quotations", tags=["Quotations"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["Attachments"])
api_router.include_router(dispatches.router, prefix="/dispatches", tags=["Dispatches"])
api_router.include_router(outstanding.router, prefix="/outstanding", tags=["Outstanding"])
