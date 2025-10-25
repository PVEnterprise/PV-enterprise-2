/**
 * TypeScript type definitions for the application.
 */

export interface User {
  id: string;
  email: string;
  name?: string; // For employee list
  full_name?: string; // For current user
  role_id: string;
  role_name?: string; // Role name for quick access
  phone?: string;
  department?: string;
  is_active: boolean;
  last_login?: string | null;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  role?: Role;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Record<string, boolean>;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  name: string;
  hospital_name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  gst_number?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  customer_id: string;
  customer?: Customer; // Populated when fetching with relationships
  sales_rep_id: string;
  status: string;
  workflow_stage: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  source?: string;
  po_number?: string;
  po_date?: string;
  po_amount?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  items?: OrderItem[];
  attachments?: Attachment[]; // Populated when fetching with relationships
}

export interface OrderItem {
  id: string;
  order_id: string;
  item_description: string;
  quantity: number;
  inventory_id?: string;
  inventory?: Inventory; // Populated when fetching with relationships
  decoded_by?: string;
  unit_price?: number;
  gst_percentage?: number;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Inventory {
  id: string;
  sku: string;
  item_name: string;
  description?: string;
  category?: string;
  manufacturer?: string;
  model_number?: string;
  unit_price: number;
  stock_quantity: number;
  reserved_quantity: number;
  reorder_level: number;
  unit_of_measure: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Quotation {
  id: string;
  quote_number: string;
  order_id: string;
  created_by: string;
  status: string;
  subtotal: number;
  gst_rate: number;
  gst_amount: number;
  discount_percentage: number;
  discount_amount: number;
  total_amount: number;
  valid_until: string;
  payment_terms?: string;
  delivery_terms?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  quotation_id?: string;
  order_id: string;
  created_by: string;
  status: string;
  invoice_date: string;
  due_date: string;
  subtotal: number;
  gst_amount: number;
  total_amount: number;
  paid_amount: number;
  payment_status: string;
  payment_terms?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Attachment {
  id: string;
  entity_type: string;
  entity_id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  file_type: string;
  uploaded_by: string;
  created_at: string;
}

export interface DashboardStats {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_revenue: number;
  pending_invoices: number;
  outstanding_amount: number;
  low_stock_items: number;
  active_customers: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type RoleName = 'executive' | 'sales_rep' | 'decoder' | 'quoter' | 'inventory_admin';
