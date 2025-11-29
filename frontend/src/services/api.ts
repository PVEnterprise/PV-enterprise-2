/**
 * API service for making HTTP requests to the backend.
 */
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : 'http://localhost:8000/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: { 'Content-Type': 'application/json' },
    });

    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) config.headers.Authorization = `Bearer ${token}`;
      return config;
    });
  }

  // Auth
  async login(email: string, password: string) {
    return (await this.client.post('/auth/login', { email, password })).data;
  }
  async getCurrentUser() {
    return (await this.client.get('/auth/me')).data;
  }

  // Customers
  getCustomers = async (params?: any) => {
    return (await this.client.get('/customers/', { params })).data;
  }
  createCustomer = async (data: any) => {
    return (await this.client.post('/customers/', data)).data;
  }
  updateCustomer = async (id: string, data: any) => {
    return (await this.client.put(`/customers/${id}`, data)).data;
  }
  deleteCustomer = async (id: string) => {
    return (await this.client.delete(`/customers/${id}`)).data;
  }

  // Orders
  getOrders = async (params?: any) => {
    return (await this.client.get('/orders/', { params })).data;
  }
  getOrder = async (id: string) => {
    return (await this.client.get(`/orders/${id}`)).data;
  }
  createOrder = async (data: any) => {
    return (await this.client.post('/orders/', data)).data;
  }
  async decodeOrderItem(orderId: string, itemId: string, data: any) {
    return (await this.client.post(`/orders/${orderId}/items/${itemId}/decode`, data)).data;
  }
  async decodeOrderItemMultiple(orderId: string, itemId: string, items: any[]) {
    return (await this.client.post(`/orders/${orderId}/items/${itemId}/decode-multiple`, { items })).data;
  }
  async updateDecodedItems(orderId: string, items: any[]) {
    return (await this.client.put(`/orders/${orderId}/decoded-items`, { items })).data;
  }
  async approveOrder(orderId: string, comments?: string) {
    return (await this.client.post(`/orders/${orderId}/approve`, { comments })).data;
  }
  async updateOrderNumber(orderId: string, newOrderNumber: string) {
    return (await this.client.patch(`/orders/${orderId}/order-number`, { new_order_number: newOrderNumber })).data;
  }

  // Inventory
  getInventory = async (params?: any) => {
    return (await this.client.get('/inventory/', { params })).data;
  }
  createInventoryItem = async (data: any) => {
    return (await this.client.post('/inventory/', data)).data;
  }
  updateInventoryItem = async (id: string, data: any) => {
    return (await this.client.put(`/inventory/${id}`, data)).data;
  }
  deleteInventoryItem = async (id: string) => {
    return (await this.client.delete(`/inventory/${id}`)).data;
  }

  // Quotations
  getQuotations = async () => {
    return (await this.client.get('/quotations/')).data;
  }
  createQuotation = async (data: any) => {
    return (await this.client.post('/quotations/', data)).data;
  }

  // Invoices
  getInvoices = async () => {
    return (await this.client.get('/invoices/')).data;
  }
  createInvoice = async (data: any) => {
    return (await this.client.post('/invoices/', data)).data;
  }

  // Dashboard
  getDashboardStats = async () => {
    return (await this.client.get('/dashboard/stats')).data;
  }

  // Employees
  getEmployees = async (params?: any) => {
    return (await this.client.get('/users/', { params })).data;
  }
  createEmployee = async (data: any) => {
    return (await this.client.post('/users/', data)).data;
  }
  updateEmployee = async (id: string, data: any) => {
    return (await this.client.put(`/users/${id}`, data)).data;
  }
  deleteEmployee = async (id: string) => {
    return (await this.client.delete(`/users/${id}`)).data;
  }

  // Roles
  getRoles = async () => {
    return (await this.client.get('/users/roles')).data;
  }

  // Order Workflow Actions (submitOrderForApproval and rejectOrder)
  submitOrderForApproval = async (orderId: string) => {
    return (await this.client.post(`/orders/${orderId}/submit-for-approval`)).data;
  }
  rejectOrder = async (orderId: string, data: { reason: string }) => {
    return (await this.client.post(`/orders/${orderId}/reject`, data)).data;
  }

  // Generic POST method for flexibility
  post = async (url: string, data?: any) => {
    return (await this.client.post(url, data)).data;
  }

  // Dispatches
  getOrderDispatches = async (orderId: string) => {
    return (await this.client.get(`/dispatches/order/${orderId}`)).data;
  }
  getDispatch = async (dispatchId: string) => {
    return (await this.client.get(`/dispatches/${dispatchId}`)).data;
  }
  createDispatch = async (data: any) => {
    return (await this.client.post('/dispatches/', data)).data;
  }

  // Outstanding
  getOutstandingByCustomer = async () => {
    return (await this.client.get('/outstanding/by-customer')).data;
  }
  getOutstandingByItem = async () => {
    return (await this.client.get('/outstanding/by-item')).data;
  }
  getOutstandingSummary = async () => {
    return (await this.client.get('/outstanding/summary')).data;
  }

  // Attachments
  getAttachments = async (orderId: string) => {
    return (await this.client.get(`/attachments/order/${orderId}`)).data;
  }

  // Price Lists
  getPriceLists = async () => {
    return (await this.client.get('/price-lists')).data;
  }
  createPriceList = async (data: any) => {
    return (await this.client.post('/price-lists', data)).data;
  }
  updatePriceList = async (id: string, data: any) => {
    return (await this.client.put(`/price-lists/${id}`, data)).data;
  }
  deletePriceList = async (id: string) => {
    return (await this.client.delete(`/price-lists/${id}`)).data;
  }
  getPriceListItems = async (priceListId: string) => {
    return (await this.client.get(`/price-lists/${priceListId}/items`)).data;
  }
  updatePriceListItem = async (priceListId: string, itemId: string, data: any) => {
    return (await this.client.put(`/price-lists/${priceListId}/items/${itemId}`, data)).data;
  }
  
  // Quotation
  submitQuotation = async (orderId: string, data: any) => {
    return (await this.client.post(`/orders/${orderId}/quotation-generated`, data)).data;
  }
  
  // Generate quotation preview PDF with custom prices
  generateQuotationPreviewPDF = async (orderId: string, data: any) => {
    const response = await this.client.post(`/orders/${orderId}/quotation/preview-pdf`, data, {
      responseType: 'blob'
    });
    return response.data;
  }
  
  // Attachments
  uploadAttachment = async (entityType: string, entityId: string, formData: FormData) => {
    console.log('API uploadAttachment called');
    console.log('FormData entries:');
    for (let pair of formData.entries()) {
      console.log(pair[0], pair[1]);
    }
    
    // Don't set Content-Type manually - let axios set it with the correct boundary
    // But we need to remove the default application/json header
    const config = {
      headers: {
        'Content-Type': undefined, // Remove default JSON header, let browser set multipart
      },
    };
    
    console.log('Request config:', config);
    
    return (await this.client.post(`/attachments/${entityType}/${entityId}`, formData, config)).data;
  }
}

export default new ApiService();
