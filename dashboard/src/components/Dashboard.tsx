import { useMemo } from 'react';
import type { CommentReport, FilterDateRange } from '../types';
import { getPersonTotals, getAverageStats, getPRMergedByPerson, getPRCreatedByPerson, getPRsByRepo, getRepoTimeStats, getActivityOverTime } from '../utils/dataTransform';
import { TotalCommentsByPerson, AvgCommentsPerPR } from './TotalCommentsByPerson';
import { PRMergedByPerson } from './PRClosedByPerson';
import { PRCreatedByPerson } from './PRCreatedByPerson';
import { PRsByRepo } from './PRsByRepo';
import { AvgTimeToComment, AvgTimeToClose } from './RepoTimeStats';
import { ActivityOverTime } from './ActivityOverTime';

interface DashboardProps {
  data: CommentReport;
  excludeBots: boolean;
  selectedRepo: string | null;
  dateRange: FilterDateRange | null;
  selectedUser: string | null;
  onDateRangeChange: (range: FilterDateRange | null) => void;
}

export function Dashboard({ data, excludeBots, selectedRepo, dateRange, selectedUser, onDateRangeChange }: DashboardProps) {
  const personTotals = useMemo(
    () => getPersonTotals(data, excludeBots, 15, selectedRepo, dateRange, selectedUser),
    [data, excludeBots, selectedRepo, dateRange, selectedUser]
  );

  const stats = useMemo(
    () => getAverageStats(data, excludeBots, selectedRepo, dateRange, selectedUser),
    [data, excludeBots, selectedRepo, dateRange, selectedUser]
  );

  const prMergedData = useMemo(
    () => getPRMergedByPerson(data, excludeBots, 15, selectedRepo, dateRange, selectedUser),
    [data, excludeBots, selectedRepo, dateRange, selectedUser]
  );

  const prCreatedData = useMemo(
    () => getPRCreatedByPerson(data, excludeBots, 15, selectedRepo, dateRange, selectedUser),
    [data, excludeBots, selectedRepo, dateRange, selectedUser]
  );

  const prsByRepoData = useMemo(
    () => getPRsByRepo(data, selectedRepo, dateRange, selectedUser),
    [data, selectedRepo, dateRange, selectedUser]
  );

  const repoTimeStats = useMemo(
    () => getRepoTimeStats(data, selectedRepo, dateRange, selectedUser),
    [data, selectedRepo, dateRange, selectedUser]
  );

  // Activity over time is NOT filtered by date range (it's the source of that filter)
  // but IS filtered by user
  const activityOverTime = useMemo(
    () => getActivityOverTime(data, excludeBots, selectedRepo, selectedUser),
    [data, excludeBots, selectedRepo, selectedUser]
  );

  const dateRangeText = useMemo(() => {
    const { since, until } = data.date_range;
    if (since && until) return `${since} to ${until}`;
    if (since) return `Since ${since}`;
    if (until) return `Until ${until}`;
    return 'All time';
  }, [data.date_range]);

  const activeFilterText = useMemo(() => {
    const parts: string[] = [];
    if (dateRange?.start && dateRange?.end) {
      parts.push(`${dateRange.start} to ${dateRange.end}`);
    } else if (dateRange?.start) {
      parts.push(`from ${dateRange.start}`);
    } else if (dateRange?.end) {
      parts.push(`until ${dateRange.end}`);
    }
    if (selectedUser) {
      parts.push(selectedUser);
    }
    return parts.length > 0 ? `Filtering: ${parts.join(' | ')}` : null;
  }, [dateRange, selectedUser]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {data.organization}
          </h1>
          <p className="text-sm text-gray-500">{dateRangeText}</p>
          {activeFilterText && (
            <p className="text-sm text-blue-600 font-medium">{activeFilterText}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Total Comments</p>
          <p className="text-2xl font-bold text-gray-900">{stats.totalComments}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Reviewers</p>
          <p className="text-2xl font-bold text-gray-900">{stats.totalPeople}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Avg per Person</p>
          <p className="text-2xl font-bold text-gray-900">{stats.averagePerPerson}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Avg per PR</p>
          <p className="text-2xl font-bold text-gray-900">{stats.avgCommentsPerPR}</p>
        </div>
      </div>

      <ActivityOverTime
        data={activityOverTime}
        dateRange={dateRange}
        onDateRangeChange={onDateRangeChange}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TotalCommentsByPerson data={personTotals} />
        <AvgCommentsPerPR data={personTotals} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PRCreatedByPerson data={prCreatedData} />
        <PRMergedByPerson data={prMergedData} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PRsByRepo data={prsByRepoData} />
        <AvgTimeToComment data={repoTimeStats} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AvgTimeToClose data={repoTimeStats} />
      </div>
    </div>
  );
}
