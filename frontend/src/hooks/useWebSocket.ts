/**
 * WebSocket hook for real-time event streaming.
 *
 * Connects to the backend WebSocket, deserializes incoming messages,
 * and dispatches them to the Zustand store. Handles reconnection
 * with exponential backoff.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useRequestStore } from '../store/requestStore';
import type { WsMessage, NetworkEvent } from '../types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/events`;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectDelayRef = useRef(RECONNECT_BASE_MS);
  const addEvent = useRequestStore((s) => s.addEvent);
  const addEvents = useRequestStore((s) => s.addEvents);
  const setConnected = useRequestStore((s) => s.setConnected);
  const setProxyRunning = useRequestStore((s) => s.setProxyRunning);
  const setRequestsPerMinute = useRequestStore((s) => s.setRequestsPerMinute);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelayRef.current = RECONNECT_BASE_MS;
    };

    ws.onmessage = (e) => {
      try {
        const msg: WsMessage = JSON.parse(e.data);

        switch (msg.type) {
          case 'request':
            addEvent(msg.data);
            break;
          case 'request_batch':
            addEvents(msg.data);
            break;
          case 'status':
            setProxyRunning(msg.data.proxy_running);
            setRequestsPerMinute(msg.data.requests_per_minute);
            break;
          case 'dropped':
            console.warn(`[NetworkGlobe] ${msg.count} events dropped (backpressure)`);
            break;
          case 'shutdown':
            ws.close();
            break;
        }
      } catch (err) {
        console.error('[NetworkGlobe] WS message parse error:', err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Reconnect with exponential backoff
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(
          reconnectDelayRef.current * 2,
          RECONNECT_MAX_MS
        );
        connect();
      }, reconnectDelayRef.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [addEvent, addEvents, setConnected, setProxyRunning, setRequestsPerMinute]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
