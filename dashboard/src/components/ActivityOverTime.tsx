import { useCallback } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Brush,
  ReferenceArea,
} from 'recharts';
import type { ActivityByDate, FilterDateRange } from '../types';
import { ChartCard } from './ChartCard';

interface ActivityOverTimeProps {
  data: ActivityByDate[];
  dateRange: FilterDateRange | null;
  onDateRangeChange: (range: FilterDateRange | null) => void;
}

interface TooltipPayload {
  payload: ActivityByDate;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const total = d.created + d.comment + d.approved + d.changes_requested + d.merged + d.closed;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.date}</p>
      <p className="text-blue-600">PRs Created: {d.created}</p>
      <p className="text-purple-600">Comments: {d.comment}</p>
      <p className="text-green-600">Approved: {d.approved}</p>
      <p className="text-orange-600">Changes Requested: {d.changes_requested}</p>
      <p className="text-emerald-600">Merged: {d.merged}</p>
      <p className="text-rose-600">Closed: {d.closed}</p>
      <p className="text-gray-500">Total: {total}</p>
    </div>
  );
}

export function ActivityOverTime({ data, dateRange, onDateRangeChange }: ActivityOverTimeProps) {
  const handleBrushChange = useCallback((brushData: { startIndex?: number; endIndex?: number }) => {
    if (brushData.startIndex === undefined || brushData.endIndex === undefined) {
      return;
    }

    // If brush covers the entire range, clear the filter
    if (brushData.startIndex === 0 && brushData.endIndex === data.length - 1) {
      onDateRangeChange(null);
      return;
    }

    const start = data[brushData.startIndex]?.date ?? null;
    const end = data[brushData.endIndex]?.date ?? null;
    onDateRangeChange({ start, end });
  }, [data, onDateRangeChange]);

  const handleClearFilter = useCallback(() => {
    onDateRangeChange(null);
  }, [onDateRangeChange]);

  if (!data || data.length === 0) {
    return (
      <ChartCard title="Activity Over Time">
        <div className="h-[300px] flex items-center justify-center text-gray-500">
          No data available
        </div>
      </ChartCard>
    );
  }

  // Find brush indices from date range
  let startIndex = 0;
  let endIndex = data.length - 1;
  if (dateRange?.start) {
    const idx = data.findIndex(d => d.date >= dateRange.start!);
    if (idx !== -1) startIndex = idx;
  }
  if (dateRange?.end) {
    const idx = data.findIndex(d => d.date > dateRange.end!);
    endIndex = idx === -1 ? data.length - 1 : Math.max(0, idx - 1);
  }

  const hasActiveFilter = dateRange?.start || dateRange?.end;

  return (
    <ChartCard title="Activity Over Time">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-gray-500">
          Drag the handles below the chart to filter by date range
        </p>
        {hasActiveFilter && (
          <button
            onClick={handleClearFilter}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            Clear date filter
          </button>
        )}
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(date: string) => {
              const d = new Date(date);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={36} />
          {hasActiveFilter && (
            <ReferenceArea
              x1={dateRange?.start ?? data[0].date}
              x2={dateRange?.end ?? data[data.length - 1].date}
              strokeOpacity={0.3}
              fill="#3b82f6"
              fillOpacity={0.1}
            />
          )}
          <Area
            type="monotone"
            dataKey="created"
            stackId="1"
            stroke="#3b82f6"
            fill="#3b82f6"
            name="PRs Created"
          />
          <Area
            type="monotone"
            dataKey="comment"
            stackId="1"
            stroke="#8b5cf6"
            fill="#8b5cf6"
            name="Comments"
          />
          <Area
            type="monotone"
            dataKey="approved"
            stackId="1"
            stroke="#22c55e"
            fill="#22c55e"
            name="Approved"
          />
          <Area
            type="monotone"
            dataKey="changes_requested"
            stackId="1"
            stroke="#f97316"
            fill="#f97316"
            name="Changes Requested"
          />
          <Area
            type="monotone"
            dataKey="merged"
            stackId="1"
            stroke="#10b981"
            fill="#10b981"
            name="Merged"
          />
          <Area
            type="monotone"
            dataKey="closed"
            stackId="1"
            stroke="#f43f5e"
            fill="#f43f5e"
            name="Closed"
          />
          <Brush
            dataKey="date"
            height={30}
            stroke="#8884d8"
            startIndex={startIndex}
            endIndex={endIndex}
            onChange={handleBrushChange}
            tickFormatter={(date: string) => {
              const d = new Date(date);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
