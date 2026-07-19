import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

interface HealthStatus {
  status: string;
  startup_step: string;
  proxy_running: boolean;
  windows_proxy_enabled: boolean;
  certificate_installed: boolean;
  geoip_available: boolean;
  sqlite_connected: boolean;
}

export default function StartupScreen({ onComplete }: { onComplete: () => void }) {
  const [completed, setCompleted] = useState(false);

  const { data: health, isError, error } = useQuery<HealthStatus>({
    queryKey: ['health-startup'],
    queryFn: async () => {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Backend not reachable');
      return res.json();
    },
    refetchInterval: completed ? false : 500,
  });

  useEffect(() => {
    if (health?.startup_step === 'Complete') {
      // Delay slightly for UX so user sees the final checklist
      setTimeout(() => {
        setCompleted(true);
        setTimeout(onComplete, 1000);
      }, 1000);
    }
  }, [health, onComplete]);

  const steps = [
    { key: 'Connecting database', checked: health?.sqlite_connected },
    { key: 'Checking certificates', checked: health?.certificate_installed },
    { key: 'Loading GeoIP database', checked: health?.geoip_available },
    { key: 'Starting proxy', checked: health?.proxy_running },
  ];

  return (
    <AnimatePresence>
      {!completed && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 backdrop-blur-xl"
        >
          <div className="flex max-w-md flex-col items-center justify-center space-y-8 p-8 text-center">
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
              <h1 className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-3xl font-bold text-transparent">
                Starting NetworkGlobe
              </h1>
              <p className="text-sm font-medium text-slate-400">
                {isError ? 'Connection failed' : health?.startup_step || 'Initializing components...'}
              </p>
            </div>

            {isError ? (
              <div className="flex items-center space-x-2 text-rose-400">
                <XCircle className="h-5 w-5" />
                <span className="text-sm">Cannot connect to backend: {(error as Error).message}</span>
              </div>
            ) : (
              <div className="w-full space-y-4 rounded-xl border border-white/5 bg-white/5 p-6 shadow-2xl backdrop-blur-md">
                {steps.map((step, i) => (
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
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
