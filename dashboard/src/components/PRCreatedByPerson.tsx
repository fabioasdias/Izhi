import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PRCreatedByPerson as PRCreatedData } from '../types';
import { ChartCard } from './ChartCard';

interface PRCreatedByPersonProps {
  data: PRCreatedData[];
}

interface TooltipPayload {
  payload: PRCreatedData;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.name}</p>
      <p>PRs created: {d.created}</p>
    </div>
  );
}

export function PRCreatedByPerson({ data }: PRCreatedByPersonProps) {
  return (
    <ChartCard title="PRs Created by Person">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="created" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
