import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { RepoPRCounts } from '../types';
import { ChartCard } from './ChartCard';

interface PRsByRepoProps {
  data: { repo: string; counts: RepoPRCounts }[];
}

interface ChartData {
  repo: string;
  open: number;
  merged: number;
  closed: number;
  total: number;
}

interface TooltipPayload {
  payload: ChartData;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.repo}</p>
      <p className="text-amber-600">Open: {d.open}</p>
      <p className="text-emerald-600">Merged: {d.merged}</p>
      <p className="text-rose-600">Closed: {d.closed}</p>
      <p className="text-gray-500">Total: {d.total}</p>
    </div>
  );
}

export function PRsByRepo({ data }: PRsByRepoProps) {
  const chartData: ChartData[] = (data ?? [])
    .slice(0, 15)
    .map(({ repo, counts }) => ({
      repo,
      open: counts.open,
      merged: counts.merged,
      closed: counts.closed,
      total: counts.open + counts.merged + counts.closed,
    }));

  return (
    <ChartCard title="PRs by Repository">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis
            type="category"
            dataKey="repo"
            width={120}
            tick={{ fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="open" stackId="a" fill="#f59e0b" name="Open" />
          <Bar dataKey="merged" stackId="a" fill="#10b981" name="Merged" />
          <Bar dataKey="closed" stackId="a" fill="#f43f5e" name="Closed" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
