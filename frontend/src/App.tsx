import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api/client';
import { OverviewKPIs, AttentionItem } from './types';
import { useLiveOpsSocket } from './hooks/useLiveOpsSocket';
import { Navbar } from './components/layout/Navbar';
import { OverviewTab } from './components/overview/OverviewTab';
import { BookingsTable } from './components/bookings/BookingsTable';
import { AnalyticsTab } from './components/analytics/AnalyticsTab';
import { MechanicsList } from './components/mechanics/MechanicsList';
import { CustomersList } from './components/customers/CustomersList';
import { BookingDetailModal } from './components/booking-detail/BookingDetailModal';
import { Bell, Sparkles } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [attentionItems, setAttentionItems] = useState<AttentionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [selectedBookingId, setSelectedBookingId] = useState<number | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const [isSimulating, setIsSimulating] = useState(false);
  const [isSimulatingAction, setIsSimulatingAction] = useState(false);
  const [liveNotification, setLiveNotification] = useState<{ title: string; subtitle: string } | null>(null);

  // Fetch overview data
  const fetchOverviewData = useCallback(async () => {
    try {
      const [kpiRes, attRes] = await Promise.all([
        api.getOverviewKPIs(),
        api.getAttentionItems(),
      ]);
      setKpis(kpiRes);
      setAttentionItems(attRes.items);
    } catch (err) {
      console.error('Failed to load overview live data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle incoming real-time events from Channels WebSocket
  const handleLiveEvent = useCallback((event: string, data: any) => {
    fetchOverviewData();
    setRefreshTrigger((prev) => prev + 1);

    if (event === 'booking.updated' || event === 'booking.assigned') {
      const bNum = data.booking_number || 'Booking';
      const status = data.status || 'Updated';
      const mech = data.mechanic_name ? ` • Assigned to ${data.mechanic_name}` : '';
      setLiveNotification({
        title: `Real-Time Update: ${bNum}`,
        subtitle: `Status changed to ${status}${mech}`,
      });
      setTimeout(() => setLiveNotification(null), 4500);
    }
  }, [fetchOverviewData]);

  const { connectionState } = useLiveOpsSocket({
    onEvent: handleLiveEvent,
    enablePollingFallback: true,
    pollingIntervalMs: 12000,
  });

  useEffect(() => {
    fetchOverviewData();
  }, [fetchOverviewData]);

  // Client-side simulation interval driver
  useEffect(() => {
    let interval: number | undefined;
    if (isSimulating) {
      interval = window.setInterval(async () => {
        try {
          setIsSimulatingAction(true);
          await api.simulateDemoActivity();
        } catch (err) {
          console.error('Simulate demo event error:', err);
        } finally {
          setIsSimulatingAction(false);
        }
      }, 15000);
    }
    return () => {
      if (interval) window.clearInterval(interval);
    };
  }, [isSimulating]);

  // Manual simulate button click
  const handleManualSimulate = async () => {
    try {
      setIsSimulatingAction(true);
      const res = await api.simulateDemoActivity();
      setLiveNotification({
        title: 'Simulation Triggered',
        subtitle: res.message,
      });
      setTimeout(() => setLiveNotification(null), 4000);
    } catch (err: any) {
      console.error('Simulate manual event error:', err);
    } finally {
      setIsSimulatingAction(false);
    }
  };

  const handleAttentionAction = (item: AttentionItem) => {
    if (item.entity_type === 'booking') {
      setSelectedBookingId(item.entity_id);
    } else if (item.entity_type === 'mechanic') {
      setActiveTab('mechanics');
    }
  };

  const handleViewBookingsWithFilter = (filter?: string) => {
    setStatusFilter(filter || '');
    setActiveTab('bookings');
  };

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col font-sans selection:bg-orange-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          if (tab !== 'bookings') setStatusFilter(undefined);
          setActiveTab(tab);
        }}
        connectionState={connectionState}
        isSimulating={isSimulating}
        setIsSimulating={setIsSimulating}
        onManualSimulate={handleManualSimulate}
        isSimulatingAction={isSimulatingAction}
      />

      {/* Real-time Notification Banner */}
      {liveNotification && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full mt-4">
          <div className="bg-gradient-to-r from-orange-950/90 to-surface border border-orange-600/80 rounded-xl p-3.5 flex items-center justify-between shadow-lg shadow-orange-950/40 animate-in slide-in-from-top duration-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-orange-500 text-white flex items-center justify-center font-bold">
                <Sparkles className="w-4 h-4 animate-spin text-white" />
              </div>
              <div>
                <div className="text-xs font-bold text-white tracking-tight">{liveNotification.title}</div>
                <div className="text-xs text-orange-200/90 font-mono">{liveNotification.subtitle}</div>
              </div>
            </div>
            <button
              onClick={() => setLiveNotification(null)}
              className="text-slate-400 hover:text-white text-xs px-2 py-1"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Main Tab Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        {activeTab === 'overview' && (
          <OverviewTab
            kpis={kpis}
            attentionItems={attentionItems}
            isLoading={isLoading}
            onAttentionAction={handleAttentionAction}
            onViewBookings={handleViewBookingsWithFilter}
            onViewMechanics={() => setActiveTab('mechanics')}
          />
        )}

        {activeTab === 'bookings' && (
          <BookingsTable
            initialStatusFilter={statusFilter}
            onSelectBooking={(id) => setSelectedBookingId(id)}
            refreshTrigger={refreshTrigger}
          />
        )}

        {activeTab === 'analytics' && <AnalyticsTab />}

        {activeTab === 'mechanics' && (
          <MechanicsList
            onSelectBooking={(id) => setSelectedBookingId(id)}
            refreshTrigger={refreshTrigger}
          />
        )}

        {activeTab === 'customers' && <CustomersList />}
      </main>

      {/* Booking Detail Modal / Drawer */}
      <BookingDetailModal
        bookingId={selectedBookingId}
        onClose={() => setSelectedBookingId(null)}
        onBookingUpdated={() => {
          fetchOverviewData();
          setRefreshTrigger((prev) => prev + 1);
        }}
      />

      <footer className="border-t border-surface-border bg-surface/60 py-4 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <div>
            Instant Mechanic LiveOps Dashboard • Django + DRF + Channels + React (Vite)
          </div>
          <div className="flex items-center gap-4">
            <a
              href={`${import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://127.0.0.1:8000'}/api/docs/`}
              target="_blank"
              rel="noreferrer"
              className="text-orange-400 hover:underline font-mono"
            >
              Interactive Swagger API Docs ↗
            </a>
            <span>•</span>
            <span>Single-process ASGI Architecture (Daphne)</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
