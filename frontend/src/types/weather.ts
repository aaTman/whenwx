/**
 * Weather types and interfaces for WhenWX
 */

export interface Location {
  latitude: number;
  longitude: number;
  name?: string;
}

export interface WeatherEvent {
  id: string;
  name: string;
  description: string;
  variable: string;        // Brightband variable name (e.g., '2t', 'tprate')
  threshold: number;       // Threshold value in native units
  thresholdDisplay: number; // Threshold for display (e.g., -10 instead of 263.15K)
  operator: 'lt' | 'gt' | 'lte' | 'gte' | 'eq';
  unit: string;
}

export interface ConfidenceBand {
  earliest: string | null;
  latest: string | null;
}

export interface EventTiming {
  firstBreachTime: string | null;
  durationHours: number | null;
  nextBreachTime: string | null;
  nextDurationHours: number | null;
  modelConsistency: number;
  confidenceBand: ConfidenceBand;
}

export interface ForecastTimeSeries {
  leadTimesHours: number[];
  values: number[];
  unit: string;
}

export interface WeatherQueryResult {
  location: Location;
  event: WeatherEvent;
  timing: EventTiming;
  forecastInitTime: string;
  queryTime: string;
  dataSource: string;
  timeSeries?: ForecastTimeSeries;
  timezone?: string;
}

export interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
}

export interface QueryParams {
  lat: number;
  lon: number;
  eventId: string;
}
