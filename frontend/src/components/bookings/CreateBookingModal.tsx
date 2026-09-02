import React, { useState, useEffect } from 'react';
import { X, PlusCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../api/client';
import { Customer, Vehicle, ServiceCategory, BookingDetail } from '../../types';

interface CreateBookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBookingCreated: (booking: BookingDetail) => void;
}

export const CreateBookingModal: React.FC<CreateBookingModalProps> = ({
  isOpen,
  onClose,
  onBookingCreated,
}) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [services, setServices] = useState<ServiceCategory[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const [selectedCustomerId, setSelectedCustomerId] = useState<number | ''>('');
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | ''>('');
  const [selectedServiceId, setSelectedServiceId] = useState<number | ''>('');
  const [amount, setAmount] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load customers and services when modal opens
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setLoadingData(true);
    setError(null);

    Promise.all([
      api.getCustomers({ page_size: 100 }),
      api.getServiceCategories(),
    ])
      .then(([customersRes, servicesRes]) => {
        if (!isMounted) return;
        setCustomers(customersRes.results || []);
        setServices(servicesRes || []);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load customers/services:', err);
        setError('Failed to load customer or service category options.');
      })
      .finally(() => {
        if (isMounted) setLoadingData(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  // Derived list of vehicles for the currently selected customer
  const selectedCustomer = customers.find((c) => c.id === Number(selectedCustomerId));
  const availableVehicles: Vehicle[] = selectedCustomer?.vehicles || [];

  // When customer changes, reset selected vehicle
  const handleCustomerChange = (custId: string) => {
    const id = custId ? Number(custId) : '';
    setSelectedCustomerId(id);
    setSelectedVehicleId('');
    setError(null);
  };

  // When service changes, automatically populate amount from base_price
  const handleServiceChange = (serviceIdStr: string) => {
    const id = serviceIdStr ? Number(serviceIdStr) : '';
    setSelectedServiceId(id);
    setError(null);
    if (id) {
      const s = services.find((srv) => srv.id === id);
      if (s) {
        setAmount(String(s.base_price));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCustomerId) {
      setError('Please select a customer.');
      return;
    }
    if (!selectedVehicleId) {
      setError('Please select a vehicle belonging to this customer.');
      return;
    }
    if (!selectedServiceId) {
      setError('Please select a service category.');
      return;
    }
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount < 0) {
      setError('Please enter a valid non-negative amount.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const newBooking = await api.createBooking({
        customer: Number(selectedCustomerId),
        vehicle: Number(selectedVehicleId),
        service_category: Number(selectedServiceId),
        amount: numAmount,
      });

      onBookingCreated(newBooking);
      handleClose();
    } catch (err: any) {
      console.error('Create booking failed:', err);
      setError(err.message || 'Failed to create booking.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelectedCustomerId('');
    setSelectedVehicleId('');
    setSelectedServiceId('');
    setAmount('');
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-surface-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-surface-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-orange-400">
              <PlusCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">Create New Booking</h2>
              <p className="text-xs text-slate-400">Add an operational booking in PENDING state for dispatch</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-surface-light transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-800 rounded-xl text-xs text-red-300 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {loadingData ? (
            <div className="py-8 flex flex-col items-center justify-center gap-2 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-orange-400" />
              <span className="text-xs">Loading operational seed data...</span>
            </div>
          ) : (
            <>
              {/* Customer */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Customer <span className="text-orange-400">*</span>
                </label>
                <select
                  value={selectedCustomerId}
                  onChange={(e) => handleCustomerChange(e.target.value)}
                  className="w-full bg-background border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 transition-colors"
                  required
                >
                  <option value="">-- Select Customer --</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.phone}) • {c.vehicles?.length || 0} vehicle(s)
                    </option>
                  ))}
                </select>
              </div>

              {/* Vehicle (Filtered by selected customer) */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Customer Vehicle <span className="text-orange-400">*</span>
                </label>
                <select
                  value={selectedVehicleId}
                  onChange={(e) => setSelectedVehicleId(e.target.value ? Number(e.target.value) : '')}
                  disabled={!selectedCustomerId || availableVehicles.length === 0}
                  className="w-full bg-background border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  required
                >
                  <option value="">
                    {!selectedCustomerId
                      ? '-- Select Customer First --'
                      : availableVehicles.length === 0
                      ? '-- No Vehicles Registered for Customer --'
                      : '-- Select Vehicle --'}
                  </option>
                  {availableVehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.make} {v.model} ({v.registration_number}) - {v.vehicle_type}
                    </option>
                  ))}
                </select>
              </div>

              {/* Service Category */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Service Category <span className="text-orange-400">*</span>
                </label>
                <select
                  value={selectedServiceId}
                  onChange={(e) => handleServiceChange(e.target.value)}
                  className="w-full bg-background border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 transition-colors"
                  required
                >
                  <option value="">-- Select Service --</option>
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} (Base Price: ₹{s.base_price})
                    </option>
                  ))}
                </select>
              </div>

              {/* Amount (₹) */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Booking Amount (₹) <span className="text-orange-400">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="e.g. 2500.00"
                  className="w-full bg-background border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 transition-colors font-mono"
                  required
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Defaults to service base price. Initial status will be set to PENDING (unassigned).
                </span>
              </div>
            </>
          )}

          {/* Action Buttons */}
          <div className="pt-4 border-t border-surface-border flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-surface-light transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || loadingData || !selectedCustomerId || !selectedVehicleId || !selectedServiceId}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-orange-500 hover:bg-orange-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-orange-500/20"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Creating Booking...
                </>
              ) : (
                <>
                  <PlusCircle className="w-3.5 h-3.5" />
                  Create Booking
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
