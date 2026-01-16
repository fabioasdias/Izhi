import { useMemo } from 'react';
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
  useMedian: boolean;
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
      <p>Avg: {formatHours(d.avgTimeToComment)} ± {formatHours(d.stdDevTimeToComment)}</p>
      <p>Median: {formatHours(d.medianTimeToComment)} [{formatHours(d.minTimeToComment)} - {formatHours(d.maxTimeToComment)}]</p>
    </div>
  );
}

function TimeToCloseTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded shadow p-2 text-sm">
      <p className="font-semibold">{d.repo}</p>
      <p>Avg: {formatHours(d.avgTimeToClose)} ± {formatHours(d.stdDevTimeToClose)}</p>
      <p>Median: {formatHours(d.medianTimeToClose)} [{formatHours(d.minTimeToClose)} - {formatHours(d.maxTimeToClose)}]</p>
    </div>
  );
}

export function AvgTimeToComment({ data, useMedian }: RepoTimeStatsProps) {
  const chartData = useMemo(() => {
    return data.map(d => ({
      ...d,
      rangeErrorComment: [
        (d.medianTimeToComment ?? 0) - (d.minTimeToComment ?? 0),
        (d.maxTimeToComment ?? 0) - (d.medianTimeToComment ?? 0),
      ],
    }));
  }, [data]);

  const dataKey = useMedian ? 'medianTimeToComment' : 'avgTimeToComment';
  const filtered = chartData
    .filter(d => useMedian ? d.medianTimeToComment !== null : d.avgTimeToComment !== null)
    .sort((a, b) => {
      const aVal = useMedian ? (a.medianTimeToComment ?? 0) : (a.avgTimeToComment ?? 0);
      const bVal = useMedian ? (b.medianTimeToComment ?? 0) : (b.avgTimeToComment ?? 0);
      return bVal - aVal;
    })
    .slice(0, 15);

  const title = useMedian
    ? 'Median Time to First Comment by Repo (hours)'
    : 'Avg Time to First Comment by Repo (hours)';

  if (filtered.length === 0) {
    return (
      <ChartCard title={title}>
        <div className="h-[400px] flex items-center justify-center text-gray-500">
          No data available
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title={title}>
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
          <Bar dataKey={dataKey} fill="#3b82f6" radius={[0, 4, 4, 0]}>
            {useMedian ? (
              <ErrorBar dataKey="rangeErrorComment" direction="x" stroke="#1e40af" strokeWidth={1.5} />
            ) : (
              <ErrorBar dataKey="stdDevTimeToComment" direction="x" stroke="#1e40af" strokeWidth={1.5} />
            )}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function AvgTimeToClose({ data, useMedian }: RepoTimeStatsProps) {
  const chartData = useMemo(() => {
    return data.map(d => ({
      ...d,
      rangeErrorClose: [
        (d.medianTimeToClose ?? 0) - (d.minTimeToClose ?? 0),
        (d.maxTimeToClose ?? 0) - (d.medianTimeToClose ?? 0),
      ],
    }));
  }, [data]);

  const dataKey = useMedian ? 'medianTimeToClose' : 'avgTimeToClose';
  const filtered = chartData
    .filter(d => useMedian ? d.medianTimeToClose !== null : d.avgTimeToClose !== null)
    .sort((a, b) => {
      const aVal = useMedian ? (a.medianTimeToClose ?? 0) : (a.avgTimeToClose ?? 0);
      const bVal = useMedian ? (b.medianTimeToClose ?? 0) : (b.avgTimeToClose ?? 0);
      return bVal - aVal;
    })
    .slice(0, 15);

  const title = useMedian
    ? 'Median Time to Close by Repo (hours)'
    : 'Avg Time to Close by Repo (hours)';

  if (filtered.length === 0) {
    return (
      <ChartCard title={title}>
        <div className="h-[400px] flex items-center justify-center text-gray-500">
          No data available
        </div>
      </ChartCard>
    );
  }

  return (
    <ChartCard title={title}>
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
          <Bar dataKey={dataKey} fill="#3b82f6" radius={[0, 4, 4, 0]}>
            {useMedian ? (
              <ErrorBar dataKey="rangeErrorClose" direction="x" stroke="#1e40af" strokeWidth={1.5} />
            ) : (
              <ErrorBar dataKey="stdDevTimeToClose" direction="x" stroke="#1e40af" strokeWidth={1.5} />
            )}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
