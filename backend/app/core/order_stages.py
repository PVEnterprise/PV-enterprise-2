"""
Single source of truth for "pending" order workflow stages, shared across
dashboard and reporting endpoints. An order is terminal (no longer pending)
only once it reaches 'completed'. PRE_PO_STAGES covers everything up to and
including PO approval; POST_PO_STAGES covers approved orders still awaiting
dispatch/payment.
"""
PRE_PO_STAGES = [
    'order_request', 'decoding_approval', 'decoding',
    'quotation', 'quotation_generated', 'waiting_purchase_order', 'po_approval',
]
POST_PO_STAGES = ['inventory_check', 'payment_pending']
PENDING_WORKFLOW_STAGES = PRE_PO_STAGES + POST_PO_STAGES
