import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, RefreshCw, XCircle, ShieldAlert, Globe, DownloadCloud } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface HealthStatus {
  status: string;
  startup_step: string;
  proxy_running: boolean;
  windows_proxy_enabled: boolean;
  certificate_installed: boolean;
  geoip_available: boolean;
  sqlite_connected: boolean;
}

export default function SetupWizard({ onComplete }: { onComplete: () => void }) {
  const queryClient = useQueryClient();
  const [completed, setCompleted] = useState(false);
  
  // Form states for GeoIP
  const [accountId, setAccountId] = useState('');
  const [licenseKey, setLicenseKey] = useState('');

  const { data: health, isError, error } = useQuery<HealthStatus>({
    queryKey: ['health-startup'],
    queryFn: async () => {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Backend not reachable');
      return res.json();
    },
    refetchInterval: completed ? false : 1000,
  });

  const installCertMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/setup/certificate', { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['health-startup'] }),
  });

  const downloadGeoipMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/setup/geoip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId, license_key: licenseKey }),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['health-startup'] }),
  });

  // Check if everything is fully loaded and complete
  useEffect(() => {
    if (
      health?.startup_step === 'Complete' && 
      health?.certificate_installed && 
      health?.geoip_available
    ) {
      setTimeout(() => {
        setCompleted(true);
        setTimeout(onComplete, 1000);
      }, 1500);
    }
  }, [health, onComplete]);

  const renderCurrentStep = () => {
    if (isError) {
      return (
        <div className="flex flex-col items-center space-y-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-6 text-rose-400">
          <XCircle className="h-10 w-10" />
          <h2 className="text-lg font-bold">Backend Connection Failed</h2>
          <p className="text-sm text-center">
            Make sure NGlobe backend is running. <br/>
            {(error as Error).message}
          </p>
        </div>
      );
    }

    if (!health) {
      return (
        <div className="flex flex-col items-center space-y-4 text-slate-400">
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}>
            <RefreshCw className="h-8 w-8" />
          </motion.div>
          <p>Connecting to NGlobe...</p>
        </div>
      );
    }

    // Step 1: Certificate
    if (!health.certificate_installed) {
      return (
        <div className="flex flex-col space-y-4 rounded-xl border border-white/5 bg-white/5 p-6 backdrop-blur-md">
          <div className="flex items-center space-x-3 text-amber-400">
            <ShieldAlert className="h-6 w-6" />
            <h2 className="text-lg font-bold">HTTPS Certificate Required</h2>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            NGlobe needs to install a local CA certificate to intercept and visualize secure HTTPS traffic. 
            You will see a Windows prompt asking for permission to install the certificate.
          </p>
          <button
            onClick={() => installCertMutation.mutate()}
            disabled={installCertMutation.isPending}
            className="flex items-center justify-center space-x-2 rounded-lg bg-indigo-500 px-4 py-2 font-semibold text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {installCertMutation.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <ShieldAlert className="h-4 w-4" />
            )}
            <span>Install Certificate</span>
          </button>
          {installCertMutation.isError && (
            <p className="text-xs text-rose-400 mt-2">Error: {(installCertMutation.error as Error).message}</p>
          )}
        </div>
      );
    }

    // Step 2: GeoIP Databases
    if (!health.geoip_available) {
      return (
        <div className="flex flex-col space-y-4 rounded-xl border border-white/5 bg-white/5 p-6 backdrop-blur-md text-left">
          <div className="flex items-center space-x-3 text-cyan-400">
            <Globe className="h-6 w-6" />
            <h2 className="text-lg font-bold">MaxMind GeoLite2 Required</h2>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            To map IP addresses to physical locations, NGlobe requires the free MaxMind GeoLite2 databases. 
            Please enter your Account ID and License Key. We will download them automatically.
          </p>
          <div className="flex flex-col space-y-3">
            <input 
              type="text" 
              placeholder="Account ID"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full rounded bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none border border-slate-700 focus:border-cyan-500"
            />
            <input 
              type="password" 
              placeholder="License Key"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              className="w-full rounded bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none border border-slate-700 focus:border-cyan-500"
            />
          </div>
          <button
            onClick={() => downloadGeoipMutation.mutate()}
            disabled={downloadGeoipMutation.isPending || !accountId || !licenseKey}
            className="flex items-center justify-center space-x-2 rounded-lg bg-cyan-600 px-4 py-2 font-semibold text-white hover:bg-cyan-700 disabled:opacity-50 mt-2"
          >
            {downloadGeoipMutation.isPending ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <DownloadCloud className="h-4 w-4" />
            )}
            <span>Download Databases</span>
          </button>
          {downloadGeoipMutation.isError && (
            <p className="text-xs text-rose-400 mt-2">Error: {(downloadGeoipMutation.error as Error).message}</p>
          )}
        </div>
      );
    }

    // Step 3: All Good, just waiting for orchestrator
    return (
      <div className="w-full space-y-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 shadow-2xl backdrop-blur-md">
        <div className="flex items-center space-x-3 text-emerald-400 mb-4 justify-center">
          <CheckCircle2 className="h-8 w-8" />
          <h2 className="text-lg font-bold">Ready for Launch</h2>
        </div>
        {[
          { key: 'Connecting database', checked: health.sqlite_connected },
          { key: 'Checking certificates', checked: health.certificate_installed },
          { key: 'Loading GeoIP database', checked: health.geoip_available },
          { key: 'Starting proxy', checked: health.proxy_running },
        ].map((step, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-300">{step.key}...</span>
            {step.checked ? (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}>
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              </motion.div>
            ) : (
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
                <RefreshCw className="h-4 w-4 text-slate-500" />
              </motion.div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <AnimatePresence>
      {!completed && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950 backdrop-blur-xl"
        >
          <div className="flex w-full max-w-md flex-col items-center justify-center space-y-8 p-8 text-center">
            
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
              className="relative flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-tr from-indigo-500/20 to-cyan-500/20 p-[2px]"
            >
              <div className="flex h-full w-full items-center justify-center rounded-full bg-slate-950">
                <div className="h-16 w-16 rounded-full bg-gradient-to-tr from-indigo-500 to-cyan-500 opacity-20 blur-xl" />
                <img src="/favicon.svg" alt="Logo" className="absolute h-12 w-12" />
              </div>
            </motion.div>

            <div className="space-y-2">
              <h1 className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-3xl font-bold text-transparent tracking-tight">
                Welcome to NGlobe
              </h1>
              <p className="text-sm font-medium text-slate-400">
                {isError ? 'Setup Wizard' : health?.startup_step || 'Initializing...'}
              </p>
            </div>

            <div className="w-full">
              {renderCurrentStep()}
            </div>

          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
