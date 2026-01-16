import { useState, useMemo } from 'react';
import type { CommentReport, FilterDateRange } from './types';
import { getUniqueUsers } from './utils/dataTransform';
import { FileUpload } from './components/FileUpload';
import { Dashboard } from './components/Dashboard';

function App() {
  const [data, setData] = useState<CommentReport | null>(null);
  const [excludeBots, setExcludeBots] = useState(true);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<FilterDateRange | null>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [useMedian, setUseMedian] = useState(true);
  const [excludeOwnPR, setExcludeOwnPR] = useState(false);

  const repoList = useMemo(() => {
    if (!data) return [];
    return Object.keys(data.repositories).sort();
  }, [data]);

  const userList = useMemo(() => {
    if (!data) return [];
    return getUniqueUsers(data, excludeBots);
  }, [data, excludeBots]);

  const handleDataUpload = (newData: CommentReport) => {
    setData(newData);
    // Reset filters when new data is loaded
    setSelectedRepo(null);
    setDateRange(null);
    setSelectedUser(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <header className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            PR Comments Dashboard
          </h1>
          <div className="flex items-center gap-4">
            {data && (
              <>
                <select
                  value={selectedRepo ?? ''}
                  onChange={(e) => setSelectedRepo(e.target.value || null)}
                  className="rounded border-gray-300 text-sm text-gray-700 px-3 py-1.5"
                >
                  <option value="">All repositories</option>
                  {repoList.map((repo) => (
                    <option key={repo} value={repo}>
                      {repo}
                    </option>
                  ))}
                </select>
                <select
                  value={selectedUser ?? ''}
                  onChange={(e) => setSelectedUser(e.target.value || null)}
                  className="rounded border-gray-300 text-sm text-gray-700 px-3 py-1.5"
                >
                  <option value="">All users</option>
                  {userList.map((user) => (
                    <option key={user} value={user}>
                      {user}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={excludeBots}
                    onChange={(e) => setExcludeBots(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Exclude bots
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={useMedian}
                    onChange={(e) => setUseMedian(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Use median
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={excludeOwnPR}
                    onChange={(e) => setExcludeOwnPR(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Exclude own PRs
                </label>
              </>
            )}
            <FileUpload onUpload={handleDataUpload} />
          </div>
        </header>

        {data ? (
          <Dashboard
            data={data}
            excludeBots={excludeBots}
            selectedRepo={selectedRepo}
            dateRange={dateRange}
            selectedUser={selectedUser}
            useMedian={useMedian}
            excludeOwnPR={excludeOwnPR}
            onDateRangeChange={setDateRange}
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-32 text-gray-500">
            <svg
              className="w-16 h-16 mb-4 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-lg">Upload a JSON report to get started</p>
            <p className="text-sm mt-1">
              Generate one using: <code className="bg-gray-200 px-2 py-0.5 rounded">izhi --org your-org</code>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
