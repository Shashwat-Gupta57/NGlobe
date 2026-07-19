/**
 * Header — top bar with branding, connection status, and live stats.
 */

import { motion } from 'framer-motion';
import { useRequestStore } from '../store/requestStore';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export default function Header() {
  const isConnected = useRequestStore((s) => s.isConnected);
  const proxyRunning = useRequestStore((s) => s.proxyRunning);
  const totalCount = useRequestStore((s) => s.totalCount);
  const requestsPerMinute = useRequestStore((s) => s.requestsPerMinute);
  const events = useRequestStore((s) => s.events);

  const totalBytes = events.reduce((sum, e) => sum + e.bytes_sent + e.bytes_received, 0);

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <span className="header-logo-icon">🌐</span>
          <h1 className="header-title">NetworkGlobe</h1>
        </div>
        <span className="header-version">v0.2.0</span>
      </div>

      <div className="header-center">
        <StatBadge label="Requests" value={totalCount.toLocaleString()} />
        <StatBadge label="Rate" value={`${requestsPerMinute}/min`} />
        <StatBadge label="Traffic" value={formatBytes(totalBytes)} />
      </div>

      <div className="header-right">
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
            {proxyRunning ? 'Intercepting' : isConnected ? 'Connected' : 'Disconnected'}
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
