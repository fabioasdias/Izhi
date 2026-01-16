import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PRMergedByPerson as PRMergedData } from '../types';
import { ChartCard } from './ChartCard';

interface PRMergedByPersonProps {
  data: PRMergedData[];
}

interface TooltipPayload {
  payload: PRMergedData;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.name}</p>
      <p>PRs merged: {d.merged}</p>
    </div>
  );
}

export function PRMergedByPerson({ data }: PRMergedByPersonProps) {
  return (
    <ChartCard title="PRs Merged by Person">
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
          <Bar dataKey="merged" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
