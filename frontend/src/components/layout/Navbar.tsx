import React from 'react';
import { Activity, Wrench, Play, Pause, RefreshCw, Zap } from 'lucide-react';
import { ConnectionState } from '../../hooks/useLiveOpsSocket';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  connectionState: ConnectionState;
  isSimulating: boolean;
  setIsSimulating: (val: boolean | ((prev: boolean) => boolean)) => void;
  onManualSimulate: () => void;
  isSimulatingAction: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  connectionState,
  isSimulating,
  setIsSimulating,
  onManualSimulate,
  isSimulatingAction,
}) => {
  const tabs = [
    { id: 'overview', label: 'Overview & Attention' },
    { id: 'bookings', label: 'Bookings' },
    { id: 'analytics', label: 'Analytics' },
    { id: 'mechanics', label: 'Mechanics' },
    { id: 'customers', label: 'Customers' },
  ];

  const getConnectionPill = () => {
    switch (connectionState) {
      case 'LIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="w-2 h-2 rounded-full bg-emerald-400 -ml-3.5" />
            LIVE (WS)
          </span>
        );
      case 'RECONNECTING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-700/60 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            RECONNECTING...
          </span>
        );
      case 'POLLING_FALLBACK':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-700/60" title="WebSocket disconnected. Automatically polling every 12s.">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            POLLING (WS Fallback)
          </span>
        );
      case 'CONNECTING':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-300 border border-blue-700/60">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            CONNECTING...
          </span>
        );
    }
  };

  return (
    <header className="sticky top-0 z-30 bg-surface/95 backdrop-blur-md border-b border-surface-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-orange-600 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
              <Wrench className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">Instant Mechanic</span>
                <span className="text-xs uppercase font-mono px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 font-semibold border border-orange-500/30">
                  LiveOps
                </span>
              </div>
              <p className="text-xs text-slate-400">Real-Time Operations Cockpit</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-surface-light/60 p-1 rounded-xl border border-surface-border">
            {tabs.map((tab) => {
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    active
                      ? 'bg-orange-500 text-white shadow-md shadow-orange-500/20 font-semibold'
                      : 'text-slate-300 hover:text-white hover:bg-surface-light'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Real-time Status & Demo Simulator Controls */}
          <div className="flex items-center gap-3">
            {getConnectionPill()}

            <div className="hidden lg:flex items-center gap-2 pl-2 border-l border-surface-border">
              {/* Advance Next Job manual trigger */}
              <button
                onClick={onManualSimulate}
                disabled={isSimulatingAction}
                title="Advance one eligible booking to its next state"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-light hover:bg-surface-lighter text-slate-200 border border-surface-border transition-colors disabled:opacity-50"
              >
                {isSimulatingAction ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-orange-400" />
                ) : (
                  <Zap className="w-3.5 h-3.5 text-orange-400" />
                )}
                Advance Job
              </button>

              {/* Auto Simulate Toggle */}
              <button
                onClick={() => setIsSimulating((prev) => !prev)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                  isSimulating
                    ? 'bg-orange-600/20 text-orange-300 border-orange-500/50 shadow-inner'
                    : 'bg-surface-light text-slate-400 border-surface-border hover:text-slate-200'
                }`}
              >
                {isSimulating ? (
                  <>
                    <Pause className="w-3.5 h-3.5 text-orange-400" />
                    <span>Auto-Sim (15s)</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 text-slate-400" />
                    <span>Simulate Activity</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation bar */}
        <div className="flex md:hidden overflow-x-auto py-2 border-t border-surface-border gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1 rounded-lg text-xs whitespace-nowrap ${
                activeTab === tab.id ? 'bg-orange-500 text-white font-semibold' : 'text-slate-300 bg-surface-light'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
};
