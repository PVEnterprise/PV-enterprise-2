# Order Creation & Processing Workflow

## 🔄 Complete Order Lifecycle

### Phase 1: Order Creation (Sales Rep)

**Who:** Sales Representative  
**Permission:** `order:create`

**What They Do:**
1. Click "New Order"
2. Select customer (autocomplete search)
3. Describe requirements in plain text:
   ```
   Example:
   - 100 boxes of surgical gloves (size M)
   - 2 units of X-ray machines (Model XR-500)
   - 50 pieces of N95 surgical masks
   - 10 sets of surgical instrument kits
   ```
4. Set priority (Low, Medium, High, Urgent)
5. Add any additional notes
6. Submit

**Result:**
- Order created with status: `draft`
- Workflow stage: `order_entry`
- Single placeholder item with full requirements description
- Assigned to decoder for processing

**Key Point:** Sales doesn't need to know SKUs, quantities, or inventory details. They just describe what the customer needs in words.

---

### Phase 2: Order Decoding (Decoder)

**Who:** Decoder  
**Permission:** `order:update` (decoding)

**What They Do:**
1. View orders in "Pending Decoding" status
2. Read the requirements description
3. Map each requirement to inventory items:
   - Find matching SKU in inventory
   - Set exact quantities
   - Set unit prices
   - Break down complex requirements into multiple items
4. Update each order item with:
   - `inventory_id` (link to inventory)
   - `quantity` (actual number needed)
   - `unit_price` (from inventory)
   - Status: `decoded`

**Example Transformation:**

**Before (from Sales):**
```
Requirements: "100 boxes of surgical gloves (size M), 2 X-ray machines"
Items: [
  {
    item_description: "100 boxes of surgical gloves (size M), 2 X-ray machines",
    quantity: 1,
    status: "pending_decode"
  }
]
```

**After (by Decoder):**
```
Items: [
  {
    item_description: "Surgical Gloves - Size M",
    inventory_id: "abc-123",
    quantity: 100,
    unit_price: 15.00,
    status: "decoded"
  },
  {
    item_description: "X-Ray Machine - Model XR-500",
    inventory_id: "xyz-789",
    quantity: 2,
    unit_price: 50000.00,
    status: "decoded"
  }
]
```

**Result:**
- Order status: `pending_approval`
- Workflow stage: `decoding_complete`
- All items mapped to inventory with quantities and prices
- Ready for executive approval

---

### Phase 3: Order Approval (Executive)

**Who:** Executive (Admin)  
**Permission:** `order:approve`

**What They Do:**
1. Review decoded orders
2. Check:
   - Customer details
   - All items properly mapped
   - Quantities and prices correct
   - Total order value
3. Approve or reject with comments

**Result if Approved:**
- Order status: `approved`
- Workflow stage: `approved`
- Ready for quotation generation

**Result if Rejected:**
- Order status: `draft`
- Workflow stage: Back to previous stage
- Comments explain what needs fixing

---

### Phase 4: Quotation Generation (Quoter)

**Who:** Quoter  
**Permission:** `quotation:create`

**What They Do:**
1. View approved orders
2. Generate quotation with:
   - All order items
   - Quantities and unit prices
   - Subtotal, taxes, total
   - Terms and conditions
   - Validity period
3. Send to customer

**Result:**
- Quotation created and linked to order
- Quotation status: `draft` or `sent`
- Awaiting customer acceptance

---

### Phase 5: Invoice & Fulfillment

**After customer accepts quotation:**

1. **Quoter** creates invoice
2. **Inventory Admin** prepares dispatch
3. **Inventory Admin** creates dispatch record
4. Order status: `completed`

---

## 📋 Order Statuses

| Status | Description | Who Can Set |
|--------|-------------|-------------|
| `draft` | Initial creation, needs decoding | System (on create) |
| `pending_approval` | Decoded, awaiting approval | Decoder (after decoding) |
| `approved` | Approved by executive | Executive |
| `completed` | Fulfilled and delivered | System (after dispatch) |
| `cancelled` | Cancelled by executive | Executive |

## 🔄 Workflow Stages

| Stage | Description | Next Stage |
|-------|-------------|------------|
| `order_entry` | Sales created order | `pending_decode` |
| `pending_decode` | Waiting for decoder | `decoding` |
| `decoding` | Decoder working on it | `decoding_complete` |
| `decoding_complete` | Ready for approval | `pending_approval` |
| `pending_approval` | Waiting for executive | `approved` or back to `decoding` |
| `approved` | Approved, ready for quotation | `quotation_generation` |
| `quotation_sent` | Quotation sent to customer | `awaiting_acceptance` |
| `accepted` | Customer accepted | `fulfillment` |
| `fulfilled` | Order completed | - |

---

## 🎯 Benefits of This Workflow

### 1. **Separation of Concerns**
- Sales focuses on customer needs (what)
- Decoder focuses on inventory mapping (how)
- Executive focuses on approval (validation)
- Quoter focuses on pricing (documentation)

### 2. **Flexibility**
- Sales doesn't need inventory knowledge
- Can handle custom/special requests
- Decoder can split or combine items as needed
- Multiple items from one description

### 3. **Quality Control**
- Executive reviews before commitment
- Prevents pricing errors
- Ensures inventory availability
- Audit trail at each stage

### 4. **Scalability**
- Sales can create orders quickly
- Decoder can batch process
- Clear handoff points
- Easy to track bottlenecks

---

## 🔐 Permissions Summary

| Role | Create Order | Decode | Approve | Create Quotation | Dispatch |
|------|--------------|--------|---------|------------------|----------|
| **Sales Rep** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Decoder** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Executive** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Quoter** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Inventory Admin** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## ✅ Current Implementation Status

### ✅ Completed:
- Sales order creation with requirements description
- Autocomplete customer selection
- Priority setting
- Permission-based button visibility
- Audit tracking (created_by, created_at)

### 🚧 To Be Implemented:
- Decoder interface for item mapping
- Executive approval workflow
- Quotation generation
- Invoice creation
- Dispatch management

---

## 📝 Example: Complete Order Flow

**Step 1: Sales Creates Order**
```
Customer: Apollo Hospitals
Requirements: 
- 100 boxes of surgical gloves (size M)
- 2 units of X-ray machines
- 50 pieces of surgical masks
Priority: High
Notes: Urgent delivery needed by end of month
```

**Step 2: Decoder Maps Items**
```
Item 1: Surgical Gloves - Size M
  SKU: GLV-M-001
  Quantity: 100 boxes
  Unit Price: ₹150
  Subtotal: ₹15,000

Item 2: X-Ray Machine - Model XR-500
  SKU: XRM-500
  Quantity: 2 units
  Unit Price: ₹5,00,000
  Subtotal: ₹10,00,000

Item 3: N95 Surgical Masks
  SKU: MSK-N95-001
  Quantity: 50 pieces
  Unit Price: ₹50
  Subtotal: ₹2,500

Total: ₹10,17,500
```

**Step 3: Executive Approves**
```
Status: Approved
Comments: Approved for quotation. Check stock availability for X-ray machines.
```

**Step 4: Quoter Creates Quotation**
```
Quotation #: QT-2025-001
Valid Until: 30 days
Terms: 50% advance, 50% on delivery
Total: ₹10,17,500 + GST
```

**Step 5: Customer Accepts → Invoice → Dispatch → Complete**

---

## 🎉 Summary

The workflow is designed to be:
- ✅ **Simple** for sales (just describe needs)
- ✅ **Flexible** for decoder (map as needed)
- ✅ **Controlled** by executive (approval gate)
- ✅ **Documented** by quoter (formal pricing)
- ✅ **Tracked** by inventory (fulfillment)

**Current Status:** Phase 1 (Order Creation) is fully implemented and working!
