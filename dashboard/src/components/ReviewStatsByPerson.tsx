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
import type { ReviewStatsByPerson } from '../utils/dataTransform';
import { ChartCard } from './ChartCard';

interface ReviewStatsByPersonProps {
  data: ReviewStatsByPerson[];
}

interface TooltipPayload {
  payload: ReviewStatsByPerson;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const approvalRate = d.total > 0 ? Math.round((d.approved / d.total) * 100) : 0;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.name}</p>
      <p className="text-green-600">Approved: {d.approved}</p>
      <p className="text-orange-600">Changes Requested: {d.changesRequested}</p>
      <p className="text-gray-500">Total Reviews: {d.total}</p>
      <p className="text-gray-500">Approval Rate: {approvalRate}%</p>
    </div>
  );
}

export function ReviewsByPerson({ data }: ReviewStatsByPersonProps) {
  if (!data || data.length === 0) {
    return (
      <ChartCard title="Reviews by Person">
        <div className="h-[400px] flex items-center justify-center text-gray-500">
          No review data available
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Reviews by Person">
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
          <Legend />
          <Bar dataKey="approved" stackId="a" fill="#22c55e" name="Approved" />
          <Bar dataKey="changesRequested" stackId="a" fill="#f97316" name="Changes Requested" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
