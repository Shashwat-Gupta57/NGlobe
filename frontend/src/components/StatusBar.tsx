import { Activity, Clock, Globe2, ShieldCheck, Database } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

interface HealthStatus {
  uptime_seconds: number;
  requests_per_second: number;
  db_written: number;
}

interface AnalyticsSummary {
  total_requests: number;
  total_countries: number;
  total_organizations: number;
  total_bytes: number;
}

export default function StatusBar() {
  const { data: health } = useQuery<HealthStatus>({
    queryKey: ['health-status-bar'],
    queryFn: async () => {
      const res = await fetch('/api/health');
      return res.json();
    },
    refetchInterval: 5000,
  });

  const { data: analytics } = useQuery<AnalyticsSummary>({
    queryKey: ['analytics-summary'],
    queryFn: async () => {
      const res = await fetch('/api/analytics/summary');
      return res.json();
    },
    refetchInterval: 5000,
  });

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatUptime = (seconds: number) => {
    if (!seconds) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 flex h-8 items-center justify-between border-t border-white/5 bg-slate-950/80 px-4 backdrop-blur-md">
      <div className="flex items-center space-x-6 text-xs text-slate-400">
        <div className="flex items-center space-x-1.5">
          <Clock className="h-3.5 w-3.5 text-indigo-400" />
          <span>{formatUptime(health?.uptime_seconds || 0)}</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <Activity className="h-3.5 w-3.5 text-emerald-400" />
          <span>{health?.requests_per_second || 0} req/s</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <Database className="h-3.5 w-3.5 text-cyan-400" />
          <span>{analytics?.total_requests || 0} Total</span>
        </div>
      </div>

      <div className="flex items-center space-x-6 text-xs text-slate-400">
        <div className="flex items-center space-x-1.5">
          <Globe2 className="h-3.5 w-3.5 text-blue-400" />
          <span>{analytics?.total_countries || 0} Countries</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <ShieldCheck className="h-3.5 w-3.5 text-purple-400" />
          <span>{analytics?.total_organizations || 0} Orgs</span>
        </div>
        <div className="flex items-center space-x-1.5 text-slate-300">
          <span className="font-medium text-slate-500">DATA</span>
          <span>{formatBytes(analytics?.total_bytes || 0)}</span>
        </div>
      </div>
    </div>
  );
}
