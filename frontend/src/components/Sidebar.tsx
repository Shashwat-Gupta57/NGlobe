/**
 * Sidebar — live feed of captured requests with search and filters.
 */

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRequestStore } from '../store/requestStore';

function getMethodColor(method: string | null): string {
  switch (method) {
    case 'GET': return '#22c55e';
    case 'POST': return '#3b82f6';
    case 'PUT': return '#f59e0b';
    case 'DELETE': return '#ef4444';
    case 'PATCH': return '#a855f7';
    default: return 'var(--color-text-tertiary)';
  }
}

function getStatusColor(code: number | null): string {
  if (!code) return 'var(--color-text-tertiary)';
  if (code < 300) return '#22c55e';
  if (code < 400) return '#3b82f6';
  if (code < 500) return '#f59e0b';
  return '#ef4444';
}

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 5) return 'now';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

function getCountryFlag(code: string | null): string {
  if (!code || code.length !== 2) return '🌍';
  const offset = 127397;
  return String.fromCodePoint(...[...code.toUpperCase()].map(c => c.charCodeAt(0) + offset));
}

export default function Sidebar() {
  const filteredEvents = useRequestStore((s) => s.filteredEvents);
  const setFilters = useRequestStore((s) => s.setFilters);
  const selectedEvent = useRequestStore((s) => s.selectedEvent);
  const setSelectedEvent = useRequestStore((s) => s.setSelectedEvent);
  const [search, setSearch] = useState('');
  const listRef = useRef<HTMLDivElement>(null);

  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    setFilters({ search: value });
  }, [setFilters]);

  return (
    <aside className="sidebar">
      {/* Search */}
      <div className="sidebar-search">
        <div className="search-input-wrapper">
          <svg className="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search hosts, IPs, countries..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="search-input"
          />
          {search && (
            <button onClick={() => handleSearch('')} className="search-clear">✕</button>
          )}
        </div>
      </div>

      {/* Event count */}
      <div className="sidebar-count">
        <span>{filteredEvents.length.toLocaleString()} requests</span>
      </div>

      {/* Live feed */}
      <div className="sidebar-feed" ref={listRef}>
        <AnimatePresence initial={false}>
          {filteredEvents.slice(0, 200).map((event, i) => (
            <motion.div
              key={`${event.timestamp}-${event.hostname}-${i}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className={`feed-item ${selectedEvent === event ? 'feed-item-selected' : ''}`}
              onClick={() => setSelectedEvent(event)}
            >
              <div className="feed-item-top">
                <span className="feed-item-flag">{getCountryFlag(event.country_code)}</span>
                <span className="feed-item-host">{event.hostname}</span>
                <span className="feed-item-time">{timeAgo(event.timestamp)}</span>
              </div>
              <div className="feed-item-bottom">
                {event.method && (
                  <span className="feed-item-method" style={{ color: getMethodColor(event.method) }}>
                    {event.method}
                  </span>
                )}
                {event.status_code && (
                  <span className="feed-item-status" style={{ color: getStatusColor(event.status_code) }}>
                    {event.status_code}
                  </span>
                )}
                {event.path && (
                  <span className="feed-item-path" title={event.path}>
                    {event.path.length > 35 ? event.path.slice(0, 35) + '…' : event.path}
                  </span>
                )}
                {event.organization && (
                  <span className="feed-item-org">{event.organization}</span>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {filteredEvents.length === 0 && (
          <div className="feed-empty">
            <span className="feed-empty-icon">📡</span>
            <p>Waiting for network requests...</p>
            <p className="feed-empty-hint">Configure your browser to use proxy port 8888</p>
          </div>
        )}
      </div>

      {/* Detail panel */}
      <AnimatePresence>
        {selectedEvent && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="detail-panel"
          >
            <div className="detail-header">
              <h3>Request Detail</h3>
              <button onClick={() => setSelectedEvent(null)} className="detail-close">✕</button>
            </div>
            <DetailRow label="Host" value={selectedEvent.hostname} />
            <DetailRow label="IP" value={selectedEvent.destination_ip} />
            <DetailRow label="Method" value={selectedEvent.method || '—'} />
            <DetailRow label="Status" value={selectedEvent.status_code?.toString() || '—'} />
            <DetailRow label="Path" value={selectedEvent.path || '/'} mono />
            <DetailRow label="Country" value={`${getCountryFlag(selectedEvent.country_code)} ${selectedEvent.country_name || 'Unknown'}`} />
            <DetailRow label="City" value={selectedEvent.city || '—'} />
            <DetailRow label="Org" value={selectedEvent.organization || '—'} />
            <DetailRow label="ASN" value={selectedEvent.asn?.toString() || '—'} />
            <DetailRow label="TLS" value={selectedEvent.tls_version || '—'} />
            <DetailRow label="Latency" value={selectedEvent.latency_ms ? `${selectedEvent.latency_ms.toFixed(0)}ms` : '—'} />
            <DetailRow label="Sent" value={formatB(selectedEvent.bytes_sent)} />
            <DetailRow label="Received" value={formatB(selectedEvent.bytes_received)} />
          </motion.div>
        )}
      </AnimatePresence>
    </aside>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="detail-row">
      <span className="detail-label">{label}</span>
      <span className={`detail-value ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  );
}

function formatB(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
