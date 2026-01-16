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
import type { RepoTimeStats } from '../utils/dataTransform';
import { ChartCard } from './ChartCard';

interface RepoTimeStatsProps {
  data: RepoTimeStats[];
}

interface TooltipPayload {
  payload: RepoTimeStats;
}

function formatHours(hours: number | null): string {
  if (hours === null) return 'N/A';
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

function TimeToCommentTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.repo}</p>
      <p>Avg time to first comment: {formatHours(d.avgTimeToComment)}</p>
      {d.stdDevTimeToComment !== null && (
        <p className="text-gray-500">Std dev: ± {formatHours(d.stdDevTimeToComment)}</p>
      )}
    </div>
  );
}

function TimeToCloseTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.repo}</p>
      <p>Avg time to close: {formatHours(d.avgTimeToClose)}</p>
      {d.stdDevTimeToClose !== null && (
        <p className="text-gray-500">Std dev: ± {formatHours(d.stdDevTimeToClose)}</p>
      )}
    </div>
  );
}

export function AvgTimeToComment({ data }: RepoTimeStatsProps) {
  const filtered = data
    .filter(d => d.avgTimeToComment !== null)
    .sort((a, b) => (b.avgTimeToComment ?? 0) - (a.avgTimeToComment ?? 0))
    .slice(0, 15);

  if (filtered.length === 0) {
    return (
      <ChartCard title="Avg Time to First Comment by Repo">
        <div className="h-[400px] flex items-center justify-center text-gray-500">
          No data available
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Avg Time to First Comment by Repo (hours)">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={filtered}
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
          <Tooltip content={<TimeToCommentTooltip />} />
          <Bar dataKey="avgTimeToComment" fill="#3b82f6" radius={[0, 4, 4, 0]}>
            <ErrorBar dataKey="stdDevTimeToComment" direction="x" stroke="#1e40af" strokeWidth={1.5} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AvgTimeToClose({ data }: RepoTimeStatsProps) {
  const filtered = data
    .filter(d => d.avgTimeToClose !== null)
    .sort((a, b) => (b.avgTimeToClose ?? 0) - (a.avgTimeToClose ?? 0))
    .slice(0, 15);

  if (filtered.length === 0) {
    return (
      <ChartCard title="Avg Time to Close by Repo">
        <div className="h-[400px] flex items-center justify-center text-gray-500">
          No data available
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Avg Time to Close by Repo (hours)">
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={filtered}
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
          <Tooltip content={<TimeToCloseTooltip />} />
          <Bar dataKey="avgTimeToClose" fill="#3b82f6" radius={[0, 4, 4, 0]}>
            <ErrorBar dataKey="stdDevTimeToClose" direction="x" stroke="#1e40af" strokeWidth={1.5} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
