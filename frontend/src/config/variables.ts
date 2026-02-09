/**
 * Weather variable registry for custom thresholds.
 *
 * To add a new variable, add an entry to WEATHER_VARIABLES below.
 * The backend must also have a matching entry in api/src/variables.py.
 */

export interface WeatherVariable {
  id: string;               // Must match backend variable ID
  label: string;            // Display name
  ecmwfVariable: string;    // Primary ECMWF variable (or derived name)
  defaultThreshold: number; // Default threshold in display units
  defaultOperator: 'lt' | 'gt';
  displayUnit: string;      // Unit shown to user (e.g., '°C')
  min: number;              // Minimum allowed threshold
  max: number;              // Maximum allowed threshold
  step: number;             // Input step size
  /** Convert from display units to backend storage units */
  convertToBackend: (displayValue: number) => number;
  /** Convert from backend storage units to display units */
  convertFromBackend: (storageValue: number) => number;
}

export const WEATHER_VARIABLES: WeatherVariable[] = [
  {
    id: '2t',
    label: 'Temperature',
    ecmwfVariable: '2t',
    defaultThreshold: 0,
    defaultOperator: 'lt',
    displayUnit: '°C',
    min: -60,
    max: 60,
    step: 1,
    convertToBackend: (c: number) => c + 273.15,
    convertFromBackend: (k: number) => k - 273.15,
  },
  {
    id: 'wind_speed',
    label: 'Wind Speed',
    ecmwfVariable: 'wind_speed',
    defaultThreshold: 50,
    defaultOperator: 'gt',
    displayUnit: 'km/h',
    min: 0,
    max: 300,
    step: 5,
    convertToBackend: (kmh: number) => kmh / 3.6,
    convertFromBackend: (ms: number) => ms * 3.6,
  },
  {
    id: 'tprate',
    label: 'Precipitation',
    ecmwfVariable: 'tprate',
    defaultThreshold: 5,
    defaultOperator: 'gt',
    displayUnit: 'mm/hr',
    min: 0,
    max: 100,
    step: 1,
    convertToBackend: (mmhr: number) => mmhr / 3600,
    convertFromBackend: (kgm2s: number) => kgm2s * 3600,
  },
];

export function getVariableById(id: string): WeatherVariable | undefined {
  return WEATHER_VARIABLES.find(v => v.id === id);
}
