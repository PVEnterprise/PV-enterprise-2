/**
 * API service for making HTTP requests to the backend.
 */
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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
}

export default new ApiService();
