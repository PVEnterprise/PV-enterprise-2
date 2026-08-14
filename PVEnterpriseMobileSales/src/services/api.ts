/**
 * API service for making HTTP requests to the backend.
 * Adapted from web frontend for React Native with secure token storage.
 */
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  AuthResponse, 
  LoginRequest, 
  User, 
  Order, 
  Customer, 
  DashboardStats,
  CreateOrderRequest,
  Invoice,
  Quotation,
  Attachment
} from '@/types';
import { tokenStorage } from '@/utils/tokenStorage';
import { showErrorToast } from '@/utils/toast';

// Use your backend URL - update this based on your setup
const API_BASE_URL = 'http://143.244.140.124/api/v1';

// Log the API URL for debugging
console.log('API Base URL:', API_BASE_URL);

class ApiService {
  private client: AxiosInstance;
  public baseURL: string;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000, // 30 second timeout
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config: any) => {
        const token = await tokenStorage.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error: any) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response: any) => response,
      async (error: any) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = await tokenStorage.getRefreshToken();
            if (refreshToken) {
              const response = await this.refreshToken(refreshToken);
              await tokenStorage.storeTokens(response.access_token, response.refresh_token);
              
              // Retry original request with new token
              originalRequest.headers.Authorization = `Bearer ${response.access_token}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, clear tokens and redirect to login
            await tokenStorage.clearTokens();
            showErrorToast('Session expired. Please login again.');
            // You might want to navigate to login screen here
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    try {
      console.log('Making login request to:', `${this.baseURL}/auth/login`);
      console.log('Login payload:', JSON.stringify(credentials));
      console.log('Request headers:', this.client.defaults.headers);
      
      const response: AxiosResponse<AuthResponse> = await this.client.post('/auth/login', credentials);
      console.log('Login response status:', response.status);
      console.log('Login response headers:', response.headers);
      return response.data;
    } catch (error: any) {
      console.error('Login API error:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        headers: error.response?.headers,
        message: error.message,
        config: {
          url: error.config?.url,
          method: error.config?.method,
          headers: error.config?.headers,
          data: error.config?.data
        }
      });
      throw error; // Re-throw to be handled by the calling code
    }
  }

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.client.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.client.get('/auth/me');
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    await tokenStorage.clearTokens();
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    const response: AxiosResponse<DashboardStats> = await this.client.get('/dashboard/stats');
    return response.data;
  }

  // Customers
  async getCustomers(params?: any): Promise<Customer[]> {
    const response: AxiosResponse<Customer[]> = await this.client.get('/customers/', { params });
    return response.data;
  }

  // Orders
  async getOrders(params?: any): Promise<Order[]> {
    const response: AxiosResponse<Order[]> = await this.client.get('/orders/', { params });
    return response.data;
  }

  async getOrder(id: string): Promise<Order> {
    const response: AxiosResponse<Order> = await this.client.get(`/orders/${id}`);
    return response.data;
  }

  async createOrder(data: CreateOrderRequest): Promise<Order> {
    const response: AxiosResponse<Order> = await this.client.post('/orders/', data);
    return response.data;
  }

  // Invoices
  async getInvoices(): Promise<Invoice[]> {
    const response: AxiosResponse<Invoice[]> = await this.client.get('/invoices/');
    return response.data;
  }

  async downloadInvoicePdf(invoiceId: string): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(`/invoices/${invoiceId}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Quotations
  async getQuotations(): Promise<Quotation[]> {
    const response: AxiosResponse<Quotation[]> = await this.client.get('/quotations/');
    return response.data;
  }

  async downloadQuotationPdf(quotationId: string): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(`/quotations/${quotationId}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async downloadOrderQuotationPdf(orderId: string): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(`/orders/${orderId}/estimate-pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async downloadDispatchInvoicePdf(dispatchId: string): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(`/dispatches/${dispatchId}/invoice/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async downloadDispatchDcPdf(dispatchId: string): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(`/dispatches/${dispatchId}/dc/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async downloadAttachment(attachmentId: string): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(`/attachments/download/${attachmentId}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Attachments
  async getAttachments(entityType: string, entityId: string): Promise<Attachment[]> {
    const response: AxiosResponse<Attachment[]> = await this.client.get(`/attachments/${entityType}/${entityId}`);
    return response.data;
  }

  async uploadAttachment(entityType: string, entityId: string, formData: FormData): Promise<Attachment> {
    const response: AxiosResponse<Attachment> = await this.client.post(
      `/attachments/${entityType}/${entityId}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000, // 60 seconds for file uploads
      }
    );
    return response.data;
  }

  async deleteAttachment(attachmentId: string): Promise<void> {
    await this.client.delete(`/attachments/${attachmentId}`);
  }

  // Generic methods for flexibility
  async get<T>(url: string, params?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url);
    return response.data;
  }
}

export default new ApiService();
