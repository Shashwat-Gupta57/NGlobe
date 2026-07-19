import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, AlertTriangle, Key, RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';

interface Props {
  isOpen: boolean;
}

export default function GeoIPSetup({ isOpen }: Props) {
  const [accountId, setAccountId] = useState('');
  const [licenseKey, setLicenseKey] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  if (!isOpen) return null;

  const handleDownload = async () => {
    if (!accountId || !licenseKey) {
      setError('Please enter both Account ID and MaxMind license key.');
      return;
    }

    setIsDownloading(true);
    setError(null);

    try {
      const res = await fetch('/api/geoip/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId, license_key: licenseKey }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to download databases');
      }

      // Success, invalidate health query to re-check geoip status
      queryClient.invalidateQueries({ queryKey: ['health-diagnostics'] });
      queryClient.invalidateQueries({ queryKey: ['health-startup'] });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 50 }}
        className="fixed bottom-6 right-6 z-40 w-96 overflow-hidden rounded-2xl border border-rose-500/30 bg-slate-900/90 shadow-2xl backdrop-blur-xl"
      >
        <div className="flex items-center space-x-3 border-b border-rose-500/20 bg-rose-500/10 p-4">
          <AlertTriangle className="h-5 w-5 text-rose-400" />
          <h2 className="text-sm font-semibold text-rose-200">GeoLite Database Missing</h2>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-slate-300 leading-relaxed">
            Geographic visualization requires the MaxMind GeoLite2 database. NetworkGlobe uses this to map IP addresses to physical locations on the globe.
          </p>

          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                MaxMind Account ID
              </label>
              <input
                type="text"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                placeholder="e.g. 1377267"
                className="w-full rounded-lg border border-white/10 bg-black/20 py-2 px-3 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                License Key
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  value={licenseKey}
                  onChange={(e) => setLicenseKey(e.target.value)}
                  placeholder="Enter your free license key"
                  className="w-full rounded-lg border border-white/10 bg-black/20 py-2 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
            <a href="https://www.maxmind.com/en/geolite2/signup" target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors block">
              Get a free license key →
            </a>
          </div>

          {error && (
            <div className="rounded-lg bg-rose-500/10 p-3 text-sm text-rose-400 border border-rose-500/20">
              {error}
            </div>
          )}

          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="flex w-full items-center justify-center space-x-2 rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 py-2.5 text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
          >
            {isDownloading ? (
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                <RefreshCw className="h-4 w-4" />
              </motion.div>
            ) : (
              <Download className="h-4 w-4" />
            )}
            <span>{isDownloading ? 'Downloading...' : 'Download Database'}</span>
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
