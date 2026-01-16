import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ErrorBar,
} from 'recharts';
import type { PersonTotal } from '../types';
import { ChartCard } from './ChartCard';

interface TotalCommentsByPersonProps {
  data: PersonTotal[];
}

interface TooltipPayload {
  payload: PersonTotal;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.name}</p>
      <p>Total: {d.total} comments</p>
      <p>Avg per PR: {d.avgPerPR} ± {d.stdDevPerPR}</p>
      <p className="text-gray-500">{d.prsCommented} PRs reviewed</p>
    </div>
  );
}

export function TotalCommentsByPerson({ data }: TotalCommentsByPersonProps) {
  return (
    <ChartCard title="Total Comments by Person">
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
          <Bar dataKey="total" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AvgCommentsPerPR({ data }: TotalCommentsByPersonProps) {
  const sortedData = [...data].sort((a, b) => b.avgPerPR - a.avgPerPR);

  return (
    <ChartCard title="Avg Comments per PR">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={sortedData}
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
          <Bar dataKey="avgPerPR" fill="#3b82f6" radius={[0, 4, 4, 0]}>
            <ErrorBar dataKey="stdDevPerPR" direction="x" stroke="#1e40af" strokeWidth={1.5} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
