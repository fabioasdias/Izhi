import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { ActivityByDate } from '../types';
import { ChartCard } from './ChartCard';

interface ActivityOverTimeProps {
  data: ActivityByDate[];
}

interface TooltipPayload {
  payload: ActivityByDate;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const total = d.created + d.comment + d.merged + d.closed;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.date}</p>
      <p className="text-blue-600">PRs Created: {d.created}</p>
      <p className="text-purple-600">Comments: {d.comment}</p>
      <p className="text-emerald-600">Merged: {d.merged}</p>
      <p className="text-rose-600">Closed: {d.closed}</p>
      <p className="text-gray-500">Total: {total}</p>
    </div>
  );
}

export function ActivityOverTime({ data }: ActivityOverTimeProps) {
  if (!data || data.length === 0) {
    return (
      <ChartCard title="Activity Over Time">
        <div className="h-[300px] flex items-center justify-center text-gray-500">
          No data available
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Activity Over Time">
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
          <Legend />
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
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
