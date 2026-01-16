import { useMemo } from 'react';
import type { CommentReport } from '../types';
import { getPersonTotals, getAverageStats, getPRMergedByPerson, getPRCreatedByPerson, getPRsByRepo, getRepoTimeStats } from '../utils/dataTransform';
import { TotalCommentsByPerson, AvgCommentsPerPR } from './TotalCommentsByPerson';
import { PRMergedByPerson } from './PRClosedByPerson';
import { PRCreatedByPerson } from './PRCreatedByPerson';
import { PRsByRepo } from './PRsByRepo';
import { AvgTimeToComment, AvgTimeToClose } from './RepoTimeStats';

interface DashboardProps {
  data: CommentReport;
  excludeBots: boolean;
  selectedRepo: string | null;
}

export function Dashboard({ data, excludeBots, selectedRepo }: DashboardProps) {
  const personTotals = useMemo(
    () => getPersonTotals(data, excludeBots, 15, selectedRepo),
    [data, excludeBots, selectedRepo]
  );

  const stats = useMemo(
    () => getAverageStats(data, excludeBots, selectedRepo),
    [data, excludeBots, selectedRepo]
  );

  const prMergedData = useMemo(
    () => getPRMergedByPerson(data, excludeBots, 15, selectedRepo),
    [data, excludeBots, selectedRepo]
  );

  const prCreatedData = useMemo(
    () => getPRCreatedByPerson(data, excludeBots, 15, selectedRepo),
    [data, excludeBots, selectedRepo]
  );

  const prsByRepoData = useMemo(
    () => getPRsByRepo(data, selectedRepo),
    [data, selectedRepo]
  );

  const repoTimeStats = useMemo(
    () => getRepoTimeStats(data, selectedRepo),
    [data, selectedRepo]
  );

  const dateRangeText = useMemo(() => {
    const { since, until } = data.date_range;
    if (since && until) return `${since} to ${until}`;
    if (since) return `Since ${since}`;
    if (until) return `Until ${until}`;
    return 'All time';
  }, [data.date_range]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {data.organization}
          </h1>
          <p className="text-sm text-gray-500">{dateRangeText}</p>
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
