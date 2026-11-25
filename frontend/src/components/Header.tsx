/**
 * Header — top bar with branding, connection status, and live stats.
 */

import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRequestStore } from '../store/requestStore';

const getJson = (url: string) => fetch(url).then((r) => r.json());

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function Header() {
  const isConnected = useRequestStore((s) => s.isConnected);
  const totalCount = useRequestStore((s) => s.totalCount);
  const events = useRequestStore((s) => s.events);
  const queryClient = useQueryClient();
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: () => getJson('/api/health') });
  const { data: summary } = useQuery({ queryKey: ['summary'], queryFn: () => getJson('/api/analytics/summary') });
  const installCert = useMutation({
    mutationFn: () => fetch('/api/setup/certificate', { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['health'] }),
  });
  const proxyRunning = !!health?.proxy_running;
  const decrypting = !!health?.certificate_installed;
  const requestsPerMinute = summary?.requests_per_minute ?? 0;

  const totalBytes = events.reduce((sum, e) => sum + e.bytes_sent + e.bytes_received, 0);

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <span className="header-logo-icon">🌐</span>
          <h1 className="header-title">NGlobe</h1>
        </div>
        {health?.version && <span className="header-version">v{health.version}</span>}
      </div>

      <div className="header-center">
        <StatBadge label="Requests" value={totalCount.toLocaleString()} />
        <StatBadge label="Rate" value={`${requestsPerMinute}/min`} />
        <StatBadge label="Traffic" value={formatBytes(totalBytes)} />
      </div>

      <div className="header-right">
        {health && !decrypting && (
          <button
            className="stat-badge"
            style={{ cursor: 'pointer' }}
            disabled={installCert.isPending}
            onClick={() => installCert.mutate()}
            title="Trust NGlobe's certificate to see full HTTPS request details (path, status, size)"
          >
            {installCert.isPending ? 'Waiting for Windows…' : 'Enable HTTPS details'}
          </button>
        )}
        <motion.div
          className="status-indicator"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <span
            className="status-dot"
            style={{
              backgroundColor: proxyRunning
                ? 'var(--color-success)'
                : isConnected
                  ? 'var(--color-warning)'
                  : 'var(--color-danger)',
            }}
          />
          <span className="status-text">
            {!isConnected ? 'Disconnected' : !proxyRunning ? 'Proxy stopped' : decrypting ? 'Intercepting HTTPS' : 'Watching connections'}
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
