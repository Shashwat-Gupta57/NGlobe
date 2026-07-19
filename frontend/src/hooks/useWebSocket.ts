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
const FLUSH_INTERVAL_MS = 150; // ~6.6 FPS UI updates

export function useWebSocket(enabled: boolean = true) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const reconnectDelayRef = useRef(RECONNECT_BASE_MS);
  
  // Buffer for high-throughput batching
  const eventBufferRef = useRef<NetworkEvent[]>([]);
  const flushIntervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const addEvent = useRequestStore((s) => s.addEvent);
  const addEvents = useRequestStore((s) => s.addEvents);
  const setConnected = useRequestStore((s) => s.setConnected);
  const setProxyRunning = useRequestStore((s) => s.setProxyRunning);
  const setRequestsPerMinute = useRequestStore((s) => s.setRequestsPerMinute);

  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelayRef.current = RECONNECT_BASE_MS;
      
      // Start batching interval if not already running
      if (!flushIntervalRef.current) {
        flushIntervalRef.current = setInterval(() => {
          if (eventBufferRef.current.length > 0) {
            addEvents([...eventBufferRef.current]);
            eventBufferRef.current = [];
          }
        }, FLUSH_INTERVAL_MS);
      }
    };

    ws.onmessage = (e) => {
      try {
        const msg: WsMessage = JSON.parse(e.data);

        switch (msg.type) {
          case 'request':
            eventBufferRef.current.push(msg.data);
            break;
          case 'request_batch':
            eventBufferRef.current.push(...msg.data);
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
  }, [enabled, addEvent, addEvents, setConnected, setProxyRunning, setRequestsPerMinute]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (flushIntervalRef.current) clearInterval(flushIntervalRef.current);
      flushIntervalRef.current = undefined;
      if (wsRef.current) {
         wsRef.current.close();
         wsRef.current = null;
      }
    };
  }, [connect, enabled]);
}
