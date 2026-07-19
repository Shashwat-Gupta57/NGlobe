/**
 * AnalyticsPanel — charts and summary statistics.
 */

import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { motion } from 'framer-motion';

const COLORS = ['#6366f1', '#22d3ee', '#3b82f6', '#a855f7', '#f59e0b', '#22c55e', '#ec4899', '#f97316', '#14b8a6', '#8b5cf6'];

interface CountryData { country_code: string; country_name: string; count: number; bytes_total: number; }
interface OrgData { organization: string; count: number; bytes_total: number; }
interface HostData { hostname: string; count: number; bytes_total: number; last_seen: string; }
interface SummaryData { total_requests: number; unique_countries: number; unique_organizations: number; total_bytes_sent: number; total_bytes_received: number; requests_per_minute: number; }

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

// getFlag unused - removed

export default function AnalyticsPanel() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [countries, setCountries] = useState<CountryData[]>([]);
  const [orgs, setOrgs] = useState<OrgData[]>([]);
  const [hosts, setHosts] = useState<HostData[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [s, c, o, h] = await Promise.all([
          fetch('/api/analytics/summary').then(r => r.json()),
          fetch('/api/analytics/top-countries?limit=8').then(r => r.json()),
          fetch('/api/analytics/top-orgs?limit=8').then(r => r.json()),
          fetch('/api/analytics/top-hostnames?limit=10').then(r => r.json()),
        ]);
        setSummary(s);
        setCountries(c);
        setOrgs(o);
        setHosts(h);
      } catch { /* silently retry next interval */ }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <button
        className="analytics-toggle"
        onClick={() => setIsVisible(!isVisible)}
        title="Toggle Analytics"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 20V10M12 20V4M6 20v-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {isVisible && (
        <motion.div
          className="analytics-panel"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 30 }}
        >
          <div className="analytics-header">
            <h2>Analytics</h2>
            <button onClick={() => setIsVisible(false)} className="detail-close">✕</button>
          </div>

          {/* Summary cards */}
          {summary && (
            <div className="analytics-summary">
              <SummaryCard label="Total Requests" value={summary.total_requests.toLocaleString()} icon="📊" />
              <SummaryCard label="Countries" value={summary.unique_countries.toString()} icon="🌍" />
              <SummaryCard label="Organizations" value={summary.unique_organizations.toString()} icon="🏢" />
              <SummaryCard label="Traffic" value={formatBytes(summary.total_bytes_sent + summary.total_bytes_received)} icon="📡" />
            </div>
          )}

          {/* Charts */}
          <div className="analytics-charts">
            {/* Top Countries */}
            {countries.length > 0 && (
              <div className="analytics-chart glass-card">
                <h3>Top Countries</h3>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={countries} layout="vertical" margin={{ left: 60, right: 10, top: 5, bottom: 5 }}>
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="country_name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={55}
                      tickFormatter={(v: string) => v.length > 8 ? v.slice(0, 8) + '…' : v} />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f1f5f9', fontSize: 12 }}
                      formatter={(value: any) => [Number(value).toLocaleString(), 'Requests']}
                    />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {countries.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Top Organizations */}
            {orgs.length > 0 && (
              <div className="analytics-chart glass-card">
                <h3>Top Organizations</h3>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={orgs.slice(0, 6)}
                      dataKey="count"
                      nameKey="organization"
                      cx="50%"
                      cy="50%"
                      outerRadius={65}
                      strokeWidth={0}
                      label={({ name }: any) =>
                        name.length > 12 ? name.slice(0, 12) + '…' : name
                      }
                    >
                      {orgs.slice(0, 6).map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f1f5f9', fontSize: 12 }}
                      formatter={(value: any) => [Number(value).toLocaleString(), 'Requests']}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Top Hostnames Table */}
          {hosts.length > 0 && (
            <div className="analytics-table glass-card">
              <h3>Top Hostnames</h3>
              <table>
                <thead>
                  <tr>
                    <th>Hostname</th>
                    <th>Requests</th>
                    <th>Traffic</th>
                  </tr>
                </thead>
                <tbody>
                  {hosts.map((h, i) => (
                    <tr key={i}>
                      <td className="font-mono" title={h.hostname}>
                        {h.hostname.length > 30 ? h.hostname.slice(0, 30) + '…' : h.hostname}
                      </td>
                      <td>{h.count.toLocaleString()}</td>
                      <td>{formatBytes(h.bytes_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      )}
    </>
  );
}

function SummaryCard({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="summary-card glass-card">
      <span className="summary-icon">{icon}</span>
      <span className="summary-value">{value}</span>
      <span className="summary-label">{label}</span>
    </div>
  );
}
