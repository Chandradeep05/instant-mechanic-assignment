export type BookingStatus =
  | 'PENDING'
  | 'ASSIGNED'
  | 'ON_THE_WAY'
  | 'ARRIVED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED';

export type AvailabilityStatus = 'AVAILABLE' | 'OFFLINE' | 'BREAK';
export type OperationalStatus = 'AVAILABLE' | 'ASSIGNED' | 'ON_JOB' | 'BREAK' | 'OFFLINE';
export type WorkloadBadge = 'IDLE' | 'ACTIVE' | 'BUSY' | 'OVERLOADED';

export type AlertSeverity = 'CRITICAL' | 'HIGH' | 'WARNING';

export interface Vehicle {
  id: number;
  make: string;
  model: string;
  registration_number: string;
  vehicle_type: string;
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  email: string;
  created_at: string;
  vehicles: Vehicle[];
  vehicle_count: number;
  total_bookings: number;
  lifetime_value: string;
  last_booking_date: string | null;
}

export interface MechanicPrimaryBooking {
  id: number;
  booking_number: string;
  status: BookingStatus;
  service_name: string;
  customer_name: string;
}

export interface Mechanic {
  id: number;
  name: string;
  phone: string;
  availability_status: AvailabilityStatus;
  rating: string;
  created_at: string;
  active_jobs_count: number;
  total_jobs_completed: number;
  operational_status: OperationalStatus;
  primary_booking: MechanicPrimaryBooking | null;
  workload_badge: WorkloadBadge;
}

export interface ServiceCategory {
  id: number;
  name: string;
  description: string;
  base_price: string;
}

export interface BookingStatusHistory {
  id: number;
  previous_status: string;
  new_status: BookingStatus;
  changed_at: string;
  changed_by: string;
  notes: string;
}

export interface BookingListItem {
  id: number;
  booking_number: string;
  status: BookingStatus;
  amount: string;
  created_at: string;
  customer_name: string;
  customer_phone: string;
  vehicle_info: string;
  service_name: string;
  mechanic_name: string | null;
  mechanic_id: number | null;
  assigned_at: string | null;
  started_at: string | null;
  estimated_arrival_at: string | null;
  arrived_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
}

export interface BookingDetail {
  id: number;
  booking_number: string;
  status: BookingStatus;
  amount: string;
  is_demo_scenario: boolean;
  created_at: string;
  assigned_at: string | null;
  started_at: string | null;
  estimated_arrival_at: string | null;
  arrived_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  customer: Customer;
  vehicle: Vehicle;
  mechanic: Mechanic | null;
  service_category: ServiceCategory;
  status_history: BookingStatusHistory[];
  allowed_transitions: BookingStatus[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface OverviewKPIs {
  total_bookings: number;
  today_bookings: number;
  today_bookings_delta_pct: number;
  completed_bookings: number;
  pending_bookings: number;
  cancelled_bookings: number;
  total_revenue: number;
  today_revenue: number;
  today_revenue_delta_pct: number;
  active_mechanics: number;
  available_mechanics: number;
  busy_mechanics: number;
  new_customers: number;
  new_customers_delta: number;
  avg_response_time_minutes: number;
}

export interface AttentionItem {
  id: string;
  type: 'UNASSIGNED_BOOKING' | 'DELAYED_DISPATCH' | 'OVERDUE_ARRIVAL' | 'OVERLOADED_MECHANIC';
  severity: AlertSeverity;
  severity_rank: number;
  entity_type: 'booking' | 'mechanic';
  entity_id: number;
  booking_number: string | null;
  title: string;
  details: string;
  created_at: string;
  action_type: 'ASSIGN_MECHANIC' | 'VIEW_BOOKING' | 'VIEW_MECHANIC';
}

export interface AttentionResponse {
  items: AttentionItem[];
  count: number;
}

export interface BookingsTimelineDataPoint {
  timestamp: string;
  bookings: number;
  completed: number;
  cancelled?: number;
}

export interface RevenueTimelineDataPoint {
  timestamp: string;
  revenue: number;
}

export interface StatusDistributionDataPoint {
  status: BookingStatus;
  count: number;
  percentage: number;
}

export interface ServiceBreakdownDataPoint {
  id: number;
  name: string;
  total_bookings: number;
  completed_bookings: number;
  total_revenue: number;
}
