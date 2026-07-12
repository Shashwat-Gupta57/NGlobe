/**
 * GlobeMap — Interactive world map with animated request arcs.
 *
 * Uses MapLibre GL JS for the base map and deck.gl ArcLayer + ScatterplotLayer
 * for the visualization. Each request renders as a glowing arc from the user's
 * location to the destination server.
 */

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Deck } from '@deck.gl/core';
import { ArcLayer, ScatterplotLayer } from '@deck.gl/layers';
import { useRequestStore } from '../store/requestStore';
import type { NetworkEvent } from '../types';

// Default user location (will be overridden by config)
const DEFAULT_USER_LOCATION: [number, number] = [77.209, 28.6139]; // Delhi

// Dark map style (free, no API key needed)
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// Arc color palette based on protocol/status
function getArcColor(event: NetworkEvent): [number, number, number, number] {
  if (event.status_code && event.status_code >= 400) return [239, 68, 68, 200]; // red
  if (event.status_code && event.status_code >= 300) return [245, 158, 11, 200]; // amber
  if (event.method === 'POST' || event.method === 'PUT') return [59, 130, 246, 200]; // blue
  return [99, 102, 241, 200]; // indigo (default)
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
  const [userLocation] = useState<[number, number]>(DEFAULT_USER_LOCATION);
  const events = useRequestStore((s) => s.filteredEvents);
  const selectedEvent = useRequestStore((s) => s.selectedEvent);
  const setSelectedEvent = useRequestStore((s) => s.setSelectedEvent);

  // Only show events with coordinates
  const geoEvents = useMemo(
    () => events.filter((e) => e.latitude != null && e.longitude != null),
    [events]
  );

  // Deduplicate destinations for the scatter layer
  const destinations = useMemo(() => {
    const seen = new Map<string, NetworkEvent>();
    for (const e of geoEvents) {
      const key = `${e.latitude?.toFixed(2)},${e.longitude?.toFixed(2)}`;
      if (!seen.has(key)) seen.set(key, e);
    }
    return Array.from(seen.values());
  }, [geoEvents]);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: MAP_STYLE,
      center: userLocation,
      zoom: 3,
      pitch: 20,
      bearing: 0,
      antialias: true,
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

  // Initialize deck.gl overlay
  useEffect(() => {
    if (!mapLoaded || !mapContainerRef.current || deckRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    const deck = new Deck({
      parent: mapContainerRef.current,
      style: { position: 'absolute', top: 0, left: 0, zIndex: 1, pointerEvents: 'none' },
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

    // Sync deck.gl viewState with MapLibre camera
    const syncViewState = () => {
      deck.setProps({
        viewState: {
          longitude: map.getCenter().lng,
          latitude: map.getCenter().lat,
          zoom: map.getZoom(),
          pitch: map.getPitch(),
          bearing: map.getBearing(),
        },
      });
    };

    map.on('move', syncViewState);
    map.on('zoom', syncViewState);
    map.on('pitch', syncViewState);
    map.on('rotate', syncViewState);

    deckRef.current = deck;

    return () => {
      deck.finalize();
      deckRef.current = null;
    };
  }, [mapLoaded]);

  // Update deck.gl layers when data changes
  useEffect(() => {
    if (!deckRef.current) return;

    const arcLayer = new ArcLayer({
      id: 'arcs',
      data: geoEvents.slice(0, 500), // Cap for performance
      getSourcePosition: () => userLocation,
      getTargetPosition: (d: NetworkEvent) => [d.longitude!, d.latitude!],
      getSourceColor: () => [99, 102, 241, 160],
      getTargetColor: (d: NetworkEvent) => getArcColor(d),
      getWidth: (d: NetworkEvent) => (selectedEvent === d ? 4 : 2),
      getHeight: 0.4,
      greatCircle: true,
      widthMinPixels: 1,
      widthMaxPixels: 6,
      // @ts-ignore - deck.gl types
      getTilt: 0,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 80],
      onClick: ({ object }: { object: NetworkEvent }) => {
        setSelectedEvent(object);
      },
      transitions: {
        getSourcePosition: 600,
        getTargetPosition: 600,
      },
    });

    const dotLayer = new ScatterplotLayer({
      id: 'destinations',
      data: destinations,
      getPosition: (d: NetworkEvent) => [d.longitude!, d.latitude!],
      getFillColor: (d: NetworkEvent) => getTargetColor(d),
      getRadius: (d: NetworkEvent) => (selectedEvent === d ? 40000 : 25000),
      radiusMinPixels: 3,
      radiusMaxPixels: 12,
      opacity: 0.8,
      pickable: true,
      onClick: ({ object }: { object: NetworkEvent }) => {
        setSelectedEvent(object);
      },
      transitions: {
        getRadius: 300,
      },
    });

    // User location marker
    const userDot = new ScatterplotLayer({
      id: 'user-location',
      data: [{ position: userLocation }],
      getPosition: (d: { position: [number, number] }) => d.position,
      getFillColor: [99, 102, 241, 255],
      getRadius: 35000,
      radiusMinPixels: 5,
      radiusMaxPixels: 15,
      opacity: 1,
      stroked: true,
      getLineColor: [99, 102, 241, 100],
      getLineWidth: 3,
      lineWidthMinPixels: 2,
    });

    deckRef.current.setProps({ layers: [arcLayer, dotLayer, userDot] });
  }, [geoEvents, destinations, selectedEvent, userLocation, setSelectedEvent]);

  // Fly to selected event
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
