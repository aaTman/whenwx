import { useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import type { ForecastTimeSeries } from '../types/weather';
import './ForecastChart.css';

interface ForecastChartProps {
  timeSeries: ForecastTimeSeries;
  threshold: number;
  forecastInitTime: string;
  timezone: string;
}

interface ChartDataPoint {
  leadTimeHours: number;
  temperature: number;
  validTime: string;
}

function CustomTooltip({
  active,
  payload,
  timezone,
  unit,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartDataPoint }>;
  timezone: string;
  unit: string;
}) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;

  const validTimeStr = new Date(data.validTime).toLocaleString(undefined, {
    timeZone: timezone,
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  });

  return (
    <div className="forecast-tooltip">
      <p className="tooltip-temp">
        {data.temperature.toFixed(1)}{unit}
      </p>
      <p className="tooltip-lead">+{Math.round(data.leadTimeHours)}h lead time</p>
      <p className="tooltip-time">{validTimeStr}</p>
    </div>
  );
}

export function ForecastChart({
  timeSeries,
  threshold,
  forecastInitTime,
  timezone,
}: ForecastChartProps) {
  const unit = timeSeries.unit;
  const chartData = useMemo<ChartDataPoint[]>(() => {
    const initTime = new Date(forecastInitTime).getTime();
    return timeSeries.leadTimesHours.map((hours, i) => ({
      leadTimeHours: hours,
      temperature: timeSeries.values[i],
      validTime: new Date(initTime + hours * 3600 * 1000).toISOString(),
    }));
  }, [timeSeries, forecastInitTime]);

  const { dataMin, dataMax } = useMemo(() => {
    const temps = timeSeries.values;
    return {
      dataMin: Math.min(...temps),
      dataMax: Math.max(...temps),
    };
  }, [timeSeries.values]);

  // Only show threshold shading if threshold is within or near the data range
  const thresholdInView = threshold >= dataMin - 5 && threshold <= dataMax + 5;

  // Use dataMin for the bottom of shaded area (Recharts clips to visible domain)
  const areaBottom = dataMin;

  return (
    <div className="forecast-chart-wrapper">
      <h4 className="forecast-chart-title">Temperature Forecast</h4>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 10, right: 50, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
          <XAxis
            dataKey="leadTimeHours"
            stroke="rgba(255,255,255,0.4)"
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
            label={{
              value: 'Lead Time (hours)',
              fill: 'rgba(255,255,255,0.5)',
              position: 'insideBottom',
              offset: -10,
              fontSize: 12,
            }}
          />
          <YAxis
            stroke="rgba(255,255,255,0.4)"
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
            domain={['auto', 'auto']}
            label={{
              value: `Temperature (${unit})`,
              fill: 'rgba(255,255,255,0.5)',
              angle: -90,
              position: 'insideLeft',
              offset: 5,
              fontSize: 12,
            }}
          />
          <Tooltip
            content={<CustomTooltip timezone={timezone} unit={unit} />}
            cursor={{ stroke: 'rgba(255,255,255,0.2)' }}
          />
          {thresholdInView && (
            <ReferenceArea
              y1={areaBottom}
              y2={threshold}
              fill="#60a5fa"
              fillOpacity={0.14}
              stroke="none"
              ifOverflow="hidden"
            />
          )}
          {thresholdInView && (
            <ReferenceLine
              y={threshold}
              stroke="#00BAF8"
              strokeDasharray="6 4"
              strokeOpacity={0.5}
              label={{
                value: `${threshold}${unit}`,
                fill: 'rgba(0,186,248,0.6)',
                fontSize: 11,
                position: 'insideTopRight',
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="temperature"
            stroke="#00BAF8"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#00BAF8', stroke: '#0a1628', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
