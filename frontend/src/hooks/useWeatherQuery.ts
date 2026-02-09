import { useState, useEffect } from 'react';
import type { WeatherQueryResult, QueryParams } from '../types/weather';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const CACHE_KEY_PREFIX = 'whenwx_query_';
const CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutes

interface CachedResult {
  data: WeatherQueryResult;
  timestamp: number;
}

function getCacheKey(params: QueryParams): string {
  if (params.variable && params.threshold !== undefined && params.operator) {
    return `${CACHE_KEY_PREFIX}${params.lat}_${params.lon}_${params.variable}_${params.threshold}_${params.operator}`;
  }
  return `${CACHE_KEY_PREFIX}${params.lat}_${params.lon}_${params.eventId}`;
}

function getCachedData(params: QueryParams): WeatherQueryResult | null {
  try {
    const key = getCacheKey(params);
    const cached = sessionStorage.getItem(key);
    if (!cached) return null;

    const { data, timestamp }: CachedResult = JSON.parse(cached);
    // Check if cache is still valid
    if (Date.now() - timestamp < CACHE_TTL_MS) {
      return data;
    }
    // Cache expired, remove it
    sessionStorage.removeItem(key);
  } catch {
    // Invalid cache data
  }
  return null;
}

function setCachedData(params: QueryParams, data: WeatherQueryResult): void {
  try {
    const key = getCacheKey(params);
    const cached: CachedResult = { data, timestamp: Date.now() };
    sessionStorage.setItem(key, JSON.stringify(cached));
  } catch {
    // Storage full or unavailable
  }
}

interface UseWeatherQueryReturn {
  data: WeatherQueryResult | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useWeatherQuery(params: QueryParams | null): UseWeatherQueryReturn {
  const [data, setData] = useState<WeatherQueryResult | null>(() => {
    // Initialize with cached data if available
    return params ? getCachedData(params) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  useEffect(() => {
    if (!params) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    // Check cache first
    const cached = getCachedData(params);
    if (cached && fetchTrigger === 0) {
      // Use cached data, skip fetch
      setData(cached);
      return;
    }

    const controller = new AbortController();

    async function fetchData() {
      if (!params) return;

      setLoading(true);
      setError(null);

      try {
        const url = new URL(`${API_BASE_URL}/query`);
        url.searchParams.set('lat', params.lat.toString());
        url.searchParams.set('lon', params.lon.toString());

        // New mode: variable + threshold + operator
        if (params.variable && params.threshold !== undefined && params.operator) {
          url.searchParams.set('variable', params.variable);
          url.searchParams.set('threshold', params.threshold.toString());
          url.searchParams.set('operator', params.operator);
        }
        // Legacy mode: event_id
        else if (params.eventId) {
          url.searchParams.set('event_id', params.eventId);
        }

        const response = await fetch(url.toString(), {
          signal: controller.signal,
          headers: {
            'Accept': 'application/json',
          },
        });

        if (response.status === 429) {
          throw new Error('Rate limit exceeded. Please wait a minute before trying again.');
        }

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const detail = errorData.detail;
          const message = typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map((d: { msg?: string }) => d.msg).join(', ')
              : `Request failed: ${response.status}`;
          throw new Error(message);
        }

        const result = await response.json();
        setData(result);
        // Cache the successful result
        setCachedData(params, result);
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    return () => controller.abort();
  }, [params?.lat, params?.lon, params?.variable, params?.threshold, params?.operator, params?.eventId, fetchTrigger]);

  const refetch = () => setFetchTrigger(prev => prev + 1);

  return { data, loading, error, refetch };
}
