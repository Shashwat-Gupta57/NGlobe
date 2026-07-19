/**
 * NetworkGlobe — Root Application Layout
 *
 * Layout: Header (top) + GlobeMap (center) + Sidebar (right) + AnalyticsPanel (overlay)
 * WebSocket connection is established at this level.
 */

import { useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import GlobeMap from './components/GlobeMap';
import AnalyticsPanel from './components/AnalyticsPanel';
import SetupWizard from './components/SetupWizard';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [setupComplete, setSetupComplete] = useState(false);

  // Establish real-time WebSocket connection only after setup
  useWebSocket(setupComplete);

  return (
    <>
      <SetupWizard onComplete={() => setSetupComplete(true)} />
      
      {setupComplete && (
        <div className="app-layout animate-in fade-in duration-1000">
          <Header />
          <div className="app-content">
            <main className="app-main">
              <GlobeMap />
              <AnalyticsPanel />
            </main>
            <Sidebar />
          </div>
        </div>
      )}
    </>
  );
}

export default App;
