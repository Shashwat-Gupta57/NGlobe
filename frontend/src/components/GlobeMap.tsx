/**
 * GlobeMap — Interactive world map with animated packet visualization.
 *
 * Uses MapLibre GL JS for the base map and deck.gl ScatterplotLayer
 * for the visualization. Each network request spawns a small glowing
 * dot ("packet") that physically flies from the user's location to
 * the destination server. Multiple concurrent requests produce multiple
 * independent dots, visualizing real traffic volume and scale.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Deck } from '@deck.gl/core';
import { ScatterplotLayer, LineLayer } from '@deck.gl/layers';
import { useRequestStore } from '../store/requestStore';
import type { NetworkEvent } from '../types';

// Default user location (Delhi)
const DEFAULT_USER_LOCATION: [number, number] = [77.209, 28.6139];

// Dark map style
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// ── Packet particle ─────────────────────────────────────────
interface Packet {
  id: number;
  srcLng: number;
  srcLat: number;
  dstLng: number;
  dstLat: number;
  spawnTime: number;       // Date.now() when spawned
  color: [number, number, number];
}

const PACKET_TRAVEL_MS = 1500;  // Time for a packet to fly source → destination
const PACKET_FADE_MS = 400;     // Linger at destination then fade
const MAX_PACKETS = 600;        // Cap for performance

let packetIdCounter = 0;

function getPacketColor(event: NetworkEvent): [number, number, number] {
  if (event.status_code && event.status_code >= 400) return [239, 68, 68];   // red
  if (event.status_code && event.status_code >= 300) return [245, 158, 11];  // amber
  if (event.method === 'POST' || event.method === 'PUT') return [59, 130, 246]; // blue
  return [99, 102, 241]; // indigo
}

function getTargetColor(event: NetworkEvent): [number, number, number, number] {
  if (event.status_code && event.status_code >= 400) return [239, 68, 68, 180];
  return [34, 211, 238, 180]; // cyan
}

export default function GlobeMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const deckRef = useRef<Deck | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [deckReady, setDeckReady] = useState(false);
  const [userLocation] = useState<[number, number]>(DEFAULT_USER_LOCATION);
  const selectedEvent = useRequestStore((s) => s.selectedEvent);

  // ── Particle state (lives outside React to avoid re-renders) ──
  const packetsRef = useRef<Packet[]>([]);
  const lastEventCountRef = useRef(0);

  // Deduplicate destinations
  const getDestinations = useCallback((geoEvents: NetworkEvent[]) => {
    const seen = new Map<string, NetworkEvent>();
    for (const e of geoEvents) {
      const key = `${e.latitude?.toFixed(2)},${e.longitude?.toFixed(2)}`;
      if (!seen.has(key)) seen.set(key, e);
    }
    return Array.from(seen.values());
  }, []);

  // ── Initialize MapLibre ───────────────────────────────────────
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: MAP_STYLE,
      center: userLocation,
      zoom: 3,
      pitch: 20,
      bearing: 0,
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');

    map.on('load', () => {
      setMapLoaded(true);
      mapRef.current = map;
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Initialize deck.gl ────────────────────────────────────────
  useEffect(() => {
    if (!mapLoaded || !mapContainerRef.current || deckRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    const deck = new Deck({
      parent: mapContainerRef.current,
      style: { position: 'absolute', top: '0', left: '0', zIndex: '1', pointerEvents: 'none' } as Partial<CSSStyleDeclaration>,
      viewState: {
        longitude: map.getCenter().lng,
        latitude: map.getCenter().lat,
        zoom: map.getZoom(),
        pitch: map.getPitch(),
        bearing: map.getBearing(),
      },
      controller: false,
      layers: [],
    });

    const syncViewState = () => {
      deck.setProps({
        viewState: {
          longitude: map.getCenter().lng,
          latitude: map.getCenter().lat,
          zoom: map.getZoom(),
          pitch: map.getPitch(),
          bearing: map.getBearing(),
        } as any,
      });
    };

    map.on('move', syncViewState);
    map.on('zoom', syncViewState);
    map.on('pitch', syncViewState);
    map.on('rotate', syncViewState);

    deckRef.current = deck;
    setDeckReady(true);

    return () => {
      deck.finalize();
      deckRef.current = null;
      setDeckReady(false);
    };
  }, [mapLoaded]);

  // ── Animation loop ────────────────────────────────────────────
  useEffect(() => {
    if (!deckRef.current || !deckReady) return;

    let animationFrame: number;
    const THROTTLE_MS = 16; // ~60fps for smooth movement

    let lastFrameTime = 0;

    const animate = (frameTime: number) => {
      animationFrame = requestAnimationFrame(animate);

      if (frameTime - lastFrameTime < THROTTLE_MS) return;
      lastFrameTime = frameTime;

      const storeState = useRequestStore.getState();
      const currentEvents = storeState.filteredEvents;
      const currentSelected = storeState.selectedEvent;
      const now = Date.now();

      // ── Spawn new packets for new events ──────────────────────
      const geoEvents = currentEvents.filter((e) => e.latitude != null && e.longitude != null);
      const currentCount = geoEvents.length;

      if (currentCount > lastEventCountRef.current) {
        // New events arrived — spawn packets for each
        const newEvents = geoEvents.slice(0, currentCount - lastEventCountRef.current);
        for (const e of newEvents) {
          packetsRef.current.push({
            id: packetIdCounter++,
            srcLng: userLocation[0],
            srcLat: userLocation[1],
            dstLng: e.longitude!,
            dstLat: e.latitude!,
            spawnTime: (e as any)._receivedAt ?? now,
            color: getPacketColor(e),
          });
        }
        // Cap packet count
        if (packetsRef.current.length > MAX_PACKETS) {
          packetsRef.current = packetsRef.current.slice(-MAX_PACKETS);
        }
      }
      lastEventCountRef.current = currentCount;

      // ── Remove expired packets ────────────────────────────────
      const totalLife = PACKET_TRAVEL_MS + PACKET_FADE_MS;
      packetsRef.current = packetsRef.current.filter(
        (p) => now - p.spawnTime < totalLife
      );

      // ── Compute current positions for all live packets (now as beams) ────────
      const packetBeams = packetsRef.current.map((p) => {
        const elapsed = now - p.spawnTime;
        
        // Head position
        const tTravelHead = Math.min(1, elapsed / PACKET_TRAVEL_MS);
        const easeHead = 1 - Math.pow(1 - tTravelHead, 3);
        const headLng = p.srcLng + (p.dstLng - p.srcLng) * easeHead;
        const headLat = p.srcLat + (p.dstLat - p.srcLat) * easeHead;

        // Tail position (lags behind by 150ms to create a line)
        const tTravelTail = Math.max(0, Math.min(1, (elapsed - 150) / PACKET_TRAVEL_MS));
        const easeTail = 1 - Math.pow(1 - tTravelTail, 3);
        const tailLng = p.srcLng + (p.dstLng - p.srcLng) * easeTail;
        const tailLat = p.srcLat + (p.dstLat - p.srcLat) * easeTail;

        // Opacity: full during travel, fade after arrival
        let opacity = 255;
        if (elapsed > PACKET_TRAVEL_MS) {
          const fadeProg = (elapsed - PACKET_TRAVEL_MS) / PACKET_FADE_MS;
          opacity = Math.floor(255 * (1 - fadeProg));
        }

        return {
          head: [headLng, headLat] as [number, number],
          tail: [tailLng, tailLat] as [number, number],
          colorHead: [...p.color, opacity] as [number, number, number, number],
          colorTail: [...p.color, 0] as [number, number, number, number], // fade out tail
        };
      });

      // ── Build layers ──────────────────────────────────────────
      const destinations = getDestinations(geoEvents);
      const layers: any[] = [];

      // Layer 1: Flying packets (beams)
      if (packetBeams.length > 0) {
        layers.push(new LineLayer({
          id: 'packets',
          data: packetBeams,
          getSourcePosition: (d: any) => d.tail,
          getTargetPosition: (d: any) => d.head,
          getColor: (d: any) => d.colorHead,
          getWidth: 3,
          widthMinPixels: 2,
          widthMaxPixels: 5,
        }));
      }

      // Layer 2: Destination dots (always visible)
      if (destinations.length > 0) {
        layers.push(new ScatterplotLayer({
          id: 'destinations',
          data: destinations,
          getPosition: (d: NetworkEvent) => [d.longitude!, d.latitude!],
          getFillColor: (d: NetworkEvent) => getTargetColor(d),
          getRadius: (d: NetworkEvent) => {
            if (currentSelected === d) return 40000;
            // Pulse if a packet recently arrived
            const receivedAt = (d as any)._receivedAt ?? 0;
            const age = now - receivedAt;
            if (age < 600) {
              const t = age / 600;
              return 20000 + Math.sin(t * Math.PI) * 15000;
            }
            return 20000;
          },
          radiusMinPixels: 3,
          radiusMaxPixels: 10,
          opacity: 0.8,
          pickable: true,
          onClick: ({ object }: any) => {
            if (object) useRequestStore.getState().setSelectedEvent(object as NetworkEvent);
          },
        }));
      }

      // Layer 3: User location marker (pulsing)
      const pulse = Math.sin(now / 800) * 0.15 + 0.85; // 0.7–1.0
      layers.push(new ScatterplotLayer({
        id: 'user-location',
        data: [{ position: userLocation }],
        getPosition: (d: { position: [number, number] }) => d.position,
        getFillColor: [99, 102, 241, 255],
        getRadius: 35000 * pulse,
        radiusMinPixels: 5,
        radiusMaxPixels: 15,
        opacity: 1,
        stroked: true,
        getLineColor: [99, 102, 241, 100],
        getLineWidth: 3,
        lineWidthMinPixels: 2,
      }));

      deckRef.current?.setProps({ layers });
    };

    animationFrame = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animationFrame);
  }, [userLocation, getDestinations, deckReady]);

  // ── Fly to selected event ─────────────────────────────────────
  useEffect(() => {
    if (!selectedEvent?.longitude || !selectedEvent?.latitude || !mapRef.current) return;
    mapRef.current.flyTo({
      center: [
        (userLocation[0] + selectedEvent.longitude) / 2,
        (userLocation[1] + selectedEvent.latitude) / 2,
      ],
      zoom: 3.5,
      duration: 1200,
    });
  }, [selectedEvent, userLocation]);

  return (
    <div className="globe-container" ref={mapContainerRef}>
      {!mapLoaded && (
        <div className="globe-loading">
          <div className="globe-spinner" />
          <p>Loading map...</p>
        </div>
      )}
    </div>
  );
}
