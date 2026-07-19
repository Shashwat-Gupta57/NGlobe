/**
 * Zustand store for real-time network request state.
 *
 * Implements a ring buffer to keep memory bounded — new events
 * push out old events once the buffer is full.
 */

import { create } from 'zustand';
import type { NetworkEvent, FilterState } from '../types';

interface RequestStore {
  // State
  events: NetworkEvent[];
  filteredEvents: NetworkEvent[];
  selectedEvent: NetworkEvent | null;
  filters: FilterState;
  totalCount: number;
  isConnected: boolean;
  proxyRunning: boolean;
  requestsPerMinute: number;
  maxEvents: number;

  // Actions
  addEvent: (event: NetworkEvent) => void;
  addEvents: (events: NetworkEvent[]) => void;
  setSelectedEvent: (event: NetworkEvent | null) => void;
  setFilters: (filters: Partial<FilterState>) => void;
  setConnected: (connected: boolean) => void;
  setProxyRunning: (running: boolean) => void;
  setRequestsPerMinute: (rpm: number) => void;
  clearEvents: () => void;
}

const MAX_EVENTS = 1000;

function applyFilters(events: NetworkEvent[], filters: FilterState): NetworkEvent[] {
  return events.filter((e) => {
    if (filters.search) {
      const s = filters.search.toLowerCase();
      const matchesSearch =
        e.hostname.toLowerCase().includes(s) ||
        (e.destination_ip && e.destination_ip.toLowerCase().includes(s)) ||
        (e.country_name && e.country_name.toLowerCase().includes(s)) ||
        (e.organization && e.organization.toLowerCase().includes(s)) ||
        (e.path && e.path.toLowerCase().includes(s));
      if (!matchesSearch) return false;
    }
    if (filters.countries.length > 0) {
      if (!e.country_code || !filters.countries.includes(e.country_code)) return false;
    }
    if (filters.organizations.length > 0) {
      if (!e.organization || !filters.organizations.includes(e.organization)) return false;
    }
    if (filters.hostnames.length > 0) {
      if (!filters.hostnames.some((h) => e.hostname.includes(h))) return false;
    }
    return true;
  });
}

export const useRequestStore = create<RequestStore>((set, get) => ({
  events: [],
  filteredEvents: [],
  selectedEvent: null,
  filters: { search: '', countries: [], organizations: [], hostnames: [] },
  totalCount: 0,
  isConnected: false,
  proxyRunning: false,
  requestsPerMinute: 0,
  maxEvents: MAX_EVENTS,

  addEvent: (event) => {
    const { events, filters, maxEvents } = get();
    const stamped = { ...event, _receivedAt: Date.now() };
    const updated = [stamped, ...events].slice(0, maxEvents);
    const filtered = applyFilters(updated, filters);
    set({
      events: updated,
      filteredEvents: filtered,
      totalCount: get().totalCount + 1,
    });
  },

  addEvents: (newEvents) => {
    const { events, filters, maxEvents } = get();
    const now = Date.now();
    const stamped = newEvents.map(e => ({ ...e, _receivedAt: now }));
    const updated = [...stamped, ...events].slice(0, maxEvents);
    const filtered = applyFilters(updated, filters);
    set({
      events: updated,
      filteredEvents: filtered,
      totalCount: get().totalCount + newEvents.length,
    });
  },

  setSelectedEvent: (event) => set({ selectedEvent: event }),

  setFilters: (partial) => {
    const { events } = get();
    const newFilters = { ...get().filters, ...partial };
    set({
      filters: newFilters,
      filteredEvents: applyFilters(events, newFilters),
    });
  },

  setConnected: (connected) => set({ isConnected: connected }),
  setProxyRunning: (running) => set({ proxyRunning: running }),
  setRequestsPerMinute: (rpm) => set({ requestsPerMinute: rpm }),

  clearEvents: () =>
    set({
      events: [],
      filteredEvents: [],
      totalCount: 0,
      selectedEvent: null,
    }),
}));
