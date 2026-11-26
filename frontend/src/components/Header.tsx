/**
 * Header — branding, live stats, capture status and the few controls NGlobe has.
 */

import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRequestStore } from '../store/requestStore';

const getJson = (url: string) => fetch(url).then((r) => r.json());

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function Header() {
  const isConnected = useRequestStore((s) => s.isConnected);
  const totalCount = useRequestStore((s) => s.totalCount);
  const clearEvents = useRequestStore((s) => s.clearEvents);
  const queryClient = useQueryClient();
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: () => getJson('/api/health') });
  const { data: summary } = useQuery({ queryKey: ['summary'], queryFn: () => getJson('/api/analytics/summary') });
  const { data: db } = useQuery({ queryKey: ['database'], queryFn: () => getJson('/api/database') });

  const refresh = () => queryClient.invalidateQueries();
  const toggleCert = useMutation({
    mutationFn: (enable: boolean) => fetch('/api/setup/certificate', { method: enable ? 'POST' : 'DELETE' }),
    onSettled: refresh,
  });
  const clearDb = useMutation({
    mutationFn: () => fetch('/api/database', { method: 'DELETE' }),
    onSuccess: () => clearEvents(),
    onSettled: refresh,
  });

  const proxyRunning = !!health?.proxy_running;
  const decrypting = !!health?.certificate_installed;
  const allApps: boolean | null = health?.capture_all_apps ?? null;
  const traffic = (summary?.total_bytes_sent ?? 0) + (summary?.total_bytes_received ?? 0);

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <img src="/icon.png" alt="" className="header-logo-img" />
          <h1 className="header-title">NGlobe</h1>
        </div>
        {health?.version && <span className="header-version">v{health.version}</span>}
      </div>

      <div className="header-center">
        <StatBadge label="Requests" value={totalCount.toLocaleString()} />
        <StatBadge label="Rate" value={`${summary?.requests_per_minute ?? 0}/min`} />
        <StatBadge label="Traffic" value={formatBytes(traffic)} />
      </div>

      <div className="header-right">
        {db && (
          <button
            className="header-btn"
            disabled={clearDb.isPending}
            onClick={() => {
              if (confirm(`Delete all ${db.rows.toLocaleString()} saved connections (${formatBytes(db.size_bytes)})?`)) clearDb.mutate();
            }}
            title="History saved on this PC. Click to clear it."
          >
            History {formatBytes(db.size_bytes)} ✕
          </button>
        )}
        {health && (
          <button
            className="header-btn"
            disabled={toggleCert.isPending}
            onClick={() => toggleCert.mutate(!decrypting)}
            title={decrypting
              ? 'Stop decrypting HTTPS and remove NGlobe\'s certificate from Windows'
              : 'Trust NGlobe\'s certificate to see each HTTPS request\'s path, status and size'}
          >
            {toggleCert.isPending ? 'Waiting for Windows…' : decrypting ? 'HTTPS details: on' : 'HTTPS details: off'}
          </button>
        )}
        <motion.div
          className="status-indicator"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          title={allApps === false
            ? 'Admin prompt was declined or unavailable: only browsers (apps using the Windows proxy) are seen'
            : allApps ? 'Every app on this PC is being mapped' : 'Starting…'}
        >
          <span
            className="status-dot"
            style={{
              backgroundColor: proxyRunning
                ? 'var(--color-success)'
                : isConnected ? 'var(--color-warning)' : 'var(--color-danger)',
            }}
          />
          <span className="status-text">
            {!isConnected ? 'Disconnected'
              : !proxyRunning ? 'Proxy stopped'
              : allApps ? 'All apps' : allApps === false ? 'Browsers only' : 'Starting…'}
          </span>
        </motion.div>
      </div>
    </header>
  );
}

function StatBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-badge">
      <span className="stat-badge-value">{value}</span>
      <span className="stat-badge-label">{label}</span>
    </div>
  );
}
