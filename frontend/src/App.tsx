/**
 * NetworkGlobe — Root Application Layout
 *
 * Layout: Header (top) + GlobeMap (center) + Sidebar (right) + AnalyticsPanel (overlay)
 * WebSocket connection is established at this level.
 */

import Header from './components/Header';
import Sidebar from './components/Sidebar';
import GlobeMap from './components/GlobeMap';
import AnalyticsPanel from './components/AnalyticsPanel';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  // Establish real-time WebSocket connection
  useWebSocket();

  return (
    <div className="app-layout">
      <Header />
      <div className="app-content">
        <main className="app-main">
          <GlobeMap />
          <AnalyticsPanel />
        </main>
        <Sidebar />
      </div>
    </div>
  );
}

export default App;
