import { motion, AnimatePresence } from 'framer-motion';
import { Activity, CheckCircle2, XCircle, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

interface HealthStatus {
  status: string;
  uptime_seconds: number;
  proxy_running: boolean;
  windows_proxy_enabled: boolean;
  certificate_installed: boolean;
  geoip_available: boolean;
  sqlite_connected: boolean;
  ws_connections: number;
  pipeline_queue_size: number;
  requests_per_second: number;
  dropped_events: number;
  total_captured: number;
  pipeline_processed: number;
  db_written: number;
}

export default function DiagnosticsPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { data: health } = useQuery<HealthStatus>({
    queryKey: ['health-diagnostics'],
    queryFn: async () => {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Backend not reachable');
      return res.json();
    },
    refetchInterval: isOpen ? 1000 : false,
  });

  if (!isOpen) return null;

  const StatusItem = ({ label, value, good }: { label: string; value: any; good: boolean }) => (
    <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
      <span className="text-sm text-slate-300">{label}</span>
      <div className="flex items-center space-x-2">
        <span className="text-sm font-medium text-slate-100">{value}</span>
        {good ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        ) : (
          <XCircle className="h-4 w-4 text-rose-400" />
        )}
      </div>
    </div>
  );

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <div
          className="w-full max-w-lg overflow-hidden rounded-2xl border border-white/10 bg-slate-900/80 shadow-2xl backdrop-blur-xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-white/10 bg-white/5 p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-indigo-400" />
              <h2 className="text-lg font-semibold text-white">System Diagnostics</h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Subsystem Status</h3>
              <div className="rounded-xl border border-white/5 bg-slate-950/50 p-4">
                <StatusItem label="Proxy Running" value={health?.proxy_running ? 'Active' : 'Offline'} good={health?.proxy_running ?? false} />
                <StatusItem label="Windows Proxy" value={health?.windows_proxy_enabled ? 'Enabled' : 'Disabled'} good={health?.windows_proxy_enabled ?? false} />
                <StatusItem label="Certificate" value={health?.certificate_installed ? 'Installed' : 'Missing'} good={health?.certificate_installed ?? false} />
                <StatusItem label="GeoIP Database" value={health?.geoip_available ? 'Loaded' : 'Missing'} good={health?.geoip_available ?? false} />
                <StatusItem label="SQLite Database" value={health?.sqlite_connected ? 'Connected' : 'Offline'} good={health?.sqlite_connected ?? false} />
                <StatusItem label="WebSocket" value={health?.ws_connections ? `${health.ws_connections} connected` : 'Disconnected'} good={(health?.ws_connections ?? 0) > 0} />
              </div>
            </div>

            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Live Metrics</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl border border-white/5 bg-slate-950/50 p-4">
                  <div className="text-xs text-slate-400">Queue Length</div>
                  <div className="mt-1 text-2xl font-semibold text-slate-100">{health?.pipeline_queue_size || 0}</div>
                </div>
                <div className="rounded-xl border border-white/5 bg-slate-950/50 p-4">
                  <div className="text-xs text-slate-400">Dropped Events</div>
                  <div className={`mt-1 text-2xl font-semibold ${health?.dropped_events ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {health?.dropped_events || 0}
                  </div>
                </div>
                <div className="rounded-xl border border-white/5 bg-slate-950/50 p-4">
                  <div className="text-xs text-slate-400">Requests / Sec</div>
                  <div className="mt-1 text-2xl font-semibold text-indigo-400">{health?.requests_per_second || 0}</div>
                </div>
                <div className="rounded-xl border border-white/5 bg-slate-950/50 p-4">
                  <div className="text-xs text-slate-400">Uptime</div>
                  <div className="mt-1 text-2xl font-semibold text-cyan-400">{health?.uptime_seconds || 0}s</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
