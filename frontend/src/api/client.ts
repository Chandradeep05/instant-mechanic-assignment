import axios from 'axios';
import {
  OverviewKPIs,
  AttentionResponse,
  BookingListItem,
  BookingDetail,
  BookingStatus,
  Mechanic,
  Customer,
  ServiceCategory,
  PaginatedResponse,
  BookingsTimelineDataPoint,
  RevenueTimelineDataPoint,
  StatusDistributionDataPoint,
  ServiceBreakdownDataPoint,
} from '../types';

const rawApiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
const API_BASE = rawApiBase.endsWith('/') ? rawApiBase.slice(0, -1) : rawApiBase;

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Standardize error message extraction
    const serverError = error.response?.data?.error;
    if (serverError && serverError.message) {
      error.message = serverError.message;
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Dashboard & Attention
  getOverviewKPIs: async (): Promise<OverviewKPIs> => {
    const res = await apiClient.get<OverviewKPIs>('/dashboard/overview/');
    return res.data;
  },

  getAttentionItems: async (): Promise<AttentionResponse> => {
    const res = await apiClient.get<AttentionResponse>('/dashboard/attention/');
    return res.data;
  },

  // Analytics
  getAnalyticsBookings: async (range: '24h' | '7d' | '30d' = '7d'): Promise<{ range: string; data: BookingsTimelineDataPoint[] }> => {
    const res = await apiClient.get(`/analytics/bookings/?range=${range}`);
    return res.data;
  },

  getAnalyticsRevenue: async (range: '7d' | '30d' = '7d'): Promise<{ range: string; data: RevenueTimelineDataPoint[] }> => {
    const res = await apiClient.get(`/analytics/revenue/?range=${range}`);
    return res.data;
  },

  getAnalyticsStatus: async (): Promise<{ total: number; distribution: StatusDistributionDataPoint[] }> => {
    const res = await apiClient.get('/analytics/status/');
    return res.data;
  },

  getAnalyticsServices: async (): Promise<{ services: ServiceBreakdownDataPoint[] }> => {
    const res = await apiClient.get('/analytics/services/');
    return res.data;
  },

  // Bookings
  getBookings: async (params: {
    page?: number;
    status?: string;
    service_category?: number;
    search?: string;
    ordering?: string;
  }): Promise<PaginatedResponse<BookingListItem>> => {
    const res = await apiClient.get<PaginatedResponse<BookingListItem>>('/bookings/', { params });
    return res.data;
  },

  getBookingDetail: async (id: number): Promise<BookingDetail> => {
    const res = await apiClient.get<BookingDetail>(`/bookings/${id}/`);
    return res.data;
  },

  transitionBooking: async (id: number, status: BookingStatus, notes?: string): Promise<BookingDetail> => {
    const res = await apiClient.post<BookingDetail>(`/bookings/${id}/transition/`, { status, notes });
    return res.data;
  },

  assignMechanic: async (id: number, mechanicId: number, notes?: string): Promise<BookingDetail> => {
    const res = await apiClient.post<BookingDetail>(`/bookings/${id}/assign/`, {
      mechanic_id: mechanicId,
      notes,
    });
    return res.data;
  },

  // Mechanics & Customers & Services
  getMechanics: async (params?: { search?: string; ordering?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<Mechanic> | Mechanic[]> => {
    const res = await apiClient.get('/mechanics/', { params });
    return res.data;
  },

  getCustomers: async (params?: { search?: string; ordering?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<Customer>> => {
    const res = await apiClient.get('/customers/', { params });
    return res.data;
  },

  getServiceCategories: async (): Promise<ServiceCategory[]> => {
    const res = await apiClient.get<ServiceCategory[]>('/bookings/services/');
    return res.data;
  },

  // Simulator
  simulateDemoActivity: async (): Promise<{ message: string; booking?: BookingDetail }> => {
    const res = await apiClient.post('/demo/simulate/');
    return res.data;
  },
};
