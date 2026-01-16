import type { CommentReport, PersonTotal, PRMergedByPerson, RepoPRCounts, ActivityByDate, FilterDateRange, PRRecord } from '../types';

export function isBot(name: string): boolean {
  return name.endsWith('[bot]') || name === 'Copilot';
}

function getPRAuthor(pr: PRRecord): string | null {
  const createdEvent = pr.events.find(e => e.type === 'created');
  return createdEvent?.person ?? null;
}

function isInDateRange(eventDate: string, dateRange: FilterDateRange | null): boolean {
  if (!dateRange || (!dateRange.start && !dateRange.end)) return true;
  const date = eventDate.split('T')[0];
  if (dateRange.start && date < dateRange.start) return false;
  if (dateRange.end && date > dateRange.end) return false;
  return true;
}

function matchesUser(person: string, selectedUser: string | null): boolean {
  if (!selectedUser) return true;
  return person === selectedUser;
}

function calculateStdDev(values: number[], mean: number): number {
  if (values.length < 2) return 0;
  const squaredDiffs = values.map(v => Math.pow(v - mean, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
  return Math.round(Math.sqrt(variance) * 10) / 10;
}

function calculateMedian(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
  return Math.round(median * 10) / 10;
}

export function getUniqueUsers(
  report: CommentReport,
  excludeBots: boolean = true
): string[] {
  const users = new Set<string>();

  for (const prs of Object.values(report.repositories)) {
    for (const pr of prs) {
      for (const event of pr.events) {
        if (excludeBots && isBot(event.person)) continue;
        users.add(event.person);
      }
    }
  }

  return Array.from(users).sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
}

export function getPersonTotals(
  report: CommentReport,
  excludeBots: boolean = true,
  limit: number = 15,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null,
  excludeOwnPR: boolean = false
): PersonTotal[] {
  const personStats = new Map<string, { comments: number; commentsPerPR: Map<string, number> }>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const prAuthor = getPRAuthor(pr);
      for (const event of pr.events) {
        if (event.type !== 'comment') continue;
        if (excludeBots && isBot(event.person)) continue;
        if (!isInDateRange(event.date, dateRange)) continue;
        if (!matchesUser(event.person, selectedUser)) continue;
        if (excludeOwnPR && event.person === prAuthor) continue;

        const prKey = `${repo}#${pr.number}`;
        const stats = personStats.get(event.person) ?? { comments: 0, commentsPerPR: new Map() };
        stats.comments += 1;
        stats.commentsPerPR.set(prKey, (stats.commentsPerPR.get(prKey) ?? 0) + 1);
        personStats.set(event.person, stats);
      }
    }
  }

  const entries = Array.from(personStats.entries())
    .map(([name, stats]) => {
      const prsCommented = stats.commentsPerPR.size;
      const avgPerPR = prsCommented > 0 ? Math.round((stats.comments / prsCommented) * 10) / 10 : 0;
      const commentsPerPRValues = Array.from(stats.commentsPerPR.values());
      const medianPerPR = calculateMedian(commentsPerPRValues);
      const stdDevPerPR = calculateStdDev(commentsPerPRValues, avgPerPR);
      const minPerPR = commentsPerPRValues.length > 0 ? Math.min(...commentsPerPRValues) : 0;
      const maxPerPR = commentsPerPRValues.length > 0 ? Math.max(...commentsPerPRValues) : 0;
      return {
        name,
        total: stats.comments,
        prsCommented,
        avgPerPR,
        medianPerPR,
        stdDevPerPR,
        minPerPR,
        maxPerPR,
      };
    })
    .sort((a, b) => b.total - a.total)
    .slice(0, limit);

  return entries;
}

export function getPRMergedByPerson(
  report: CommentReport,
  excludeBots: boolean = true,
  limit: number = 15,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null
): PRMergedByPerson[] {
  const mergedCounts = new Map<string, number>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const mergedEvent = pr.events.find(e => e.type === 'merged');
      if (mergedEvent) {
        if (excludeBots && isBot(mergedEvent.person)) continue;
        if (!isInDateRange(mergedEvent.date, dateRange)) continue;
        if (!matchesUser(mergedEvent.person, selectedUser)) continue;
        mergedCounts.set(mergedEvent.person, (mergedCounts.get(mergedEvent.person) ?? 0) + 1);
      }
    }
  }

  const entries = Array.from(mergedCounts.entries())
    .map(([name, merged]) => ({ name, merged }))
    .sort((a, b) => b.merged - a.merged)
    .slice(0, limit);

  return entries;
}

export interface PRCreatedByPerson {
  name: string;
  created: number;
}

export function getPRCreatedByPerson(
  report: CommentReport,
  excludeBots: boolean = true,
  limit: number = 15,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null
): PRCreatedByPerson[] {
  const createdCounts = new Map<string, number>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const createdEvent = pr.events.find(e => e.type === 'created');
      if (createdEvent) {
        if (excludeBots && isBot(createdEvent.person)) continue;
        if (!isInDateRange(createdEvent.date, dateRange)) continue;
        if (!matchesUser(createdEvent.person, selectedUser)) continue;
        createdCounts.set(createdEvent.person, (createdCounts.get(createdEvent.person) ?? 0) + 1);
      }
    }
  }

  const entries = Array.from(createdCounts.entries())
    .map(([name, created]) => ({ name, created }))
    .sort((a, b) => b.created - a.created)
    .slice(0, limit);

  return entries;
}

export function getPRsByRepo(
  report: CommentReport,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null
): { repo: string; counts: RepoPRCounts }[] {
  const repoCounts: { repo: string; counts: RepoPRCounts }[] = [];

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    let open = 0;
    let merged = 0;
    let closed = 0;

    for (const pr of prs) {
      // Check if PR has any activity in date range by selected user
      const relevantEvents = pr.events.filter(e => {
        if (!isInDateRange(e.date, dateRange)) return false;
        if (!matchesUser(e.person, selectedUser)) return false;
        return true;
      });

      if (relevantEvents.length === 0) continue;

      const hasMerged = pr.events.some(e => e.type === 'merged');
      const hasClosed = pr.events.some(e => e.type === 'closed');

      if (hasMerged) {
        merged += 1;
      } else if (hasClosed) {
        closed += 1;
      } else {
        open += 1;
      }
    }

    if (open + merged + closed > 0) {
      repoCounts.push({ repo, counts: { open, merged, closed } });
    }
  }

  return repoCounts.sort((a, b) => {
    const totalA = a.counts.open + a.counts.merged + a.counts.closed;
    const totalB = b.counts.open + b.counts.merged + b.counts.closed;
    return totalB - totalA;
  });
}

export interface RepoTimeStats {
  repo: string;
  avgTimeToComment: number | null;  // hours
  medianTimeToComment: number | null;
  stdDevTimeToComment: number | null;
  minTimeToComment: number | null;
  maxTimeToComment: number | null;
  avgTimeToClose: number | null;    // hours
  medianTimeToClose: number | null;
  stdDevTimeToClose: number | null;
  minTimeToClose: number | null;
  maxTimeToClose: number | null;
}

export function getRepoTimeStats(
  report: CommentReport,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null
): RepoTimeStats[] {
  const stats: RepoTimeStats[] = [];

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    const timeToComments: number[] = [];
    const timeToClose: number[] = [];

    for (const pr of prs) {
      const createdEvent = pr.events.find(e => e.type === 'created');
      if (!createdEvent) continue;
      if (!isInDateRange(createdEvent.date, dateRange)) continue;
      if (selectedUser && !pr.events.some(e => matchesUser(e.person, selectedUser))) continue;

      const createdDate = new Date(createdEvent.date).getTime();

      // Time to first comment (by someone other than author)
      const firstComment = pr.events.find(
        e => e.type === 'comment' && e.person !== createdEvent.person
      );
      if (firstComment) {
        const commentDate = new Date(firstComment.date).getTime();
        const hoursToComment = (commentDate - createdDate) / (1000 * 60 * 60);
        if (hoursToComment >= 0) timeToComments.push(hoursToComment);
      }

      // Time to close/merge
      const closeEvent = pr.events.find(e => e.type === 'merged' || e.type === 'closed');
      if (closeEvent) {
        const closeDate = new Date(closeEvent.date).getTime();
        const hoursToClose = (closeDate - createdDate) / (1000 * 60 * 60);
        if (hoursToClose >= 0) timeToClose.push(hoursToClose);
      }
    }

    const avgComment = timeToComments.length > 0
      ? Math.round((timeToComments.reduce((a, b) => a + b, 0) / timeToComments.length) * 10) / 10
      : null;
    const medianComment = timeToComments.length > 0 ? calculateMedian(timeToComments) : null;
    const stdDevComment = avgComment !== null ? calculateStdDev(timeToComments, avgComment) : null;
    const minComment = timeToComments.length > 0 ? Math.round(Math.min(...timeToComments) * 10) / 10 : null;
    const maxComment = timeToComments.length > 0 ? Math.round(Math.max(...timeToComments) * 10) / 10 : null;

    const avgClose = timeToClose.length > 0
      ? Math.round((timeToClose.reduce((a, b) => a + b, 0) / timeToClose.length) * 10) / 10
      : null;
    const medianClose = timeToClose.length > 0 ? calculateMedian(timeToClose) : null;
    const stdDevClose = avgClose !== null ? calculateStdDev(timeToClose, avgClose) : null;
    const minClose = timeToClose.length > 0 ? Math.round(Math.min(...timeToClose) * 10) / 10 : null;
    const maxClose = timeToClose.length > 0 ? Math.round(Math.max(...timeToClose) * 10) / 10 : null;

    if (avgComment !== null || avgClose !== null) {
      stats.push({
        repo,
        avgTimeToComment: avgComment,
        medianTimeToComment: medianComment,
        stdDevTimeToComment: stdDevComment,
        minTimeToComment: minComment,
        maxTimeToComment: maxComment,
        avgTimeToClose: avgClose,
        medianTimeToClose: medianClose,
        stdDevTimeToClose: stdDevClose,
        minTimeToClose: minClose,
        maxTimeToClose: maxClose,
      });
    }
  }

  return stats.sort((a, b) => (b.avgTimeToClose ?? 0) - (a.avgTimeToClose ?? 0));
}

export interface AverageStats {
  totalComments: number;
  totalPeople: number;
  averagePerPerson: number;
  avgCommentsPerPR: number;
}

export function getAverageStats(
  report: CommentReport,
  excludeBots: boolean = true,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null,
  excludeOwnPR: boolean = false
): AverageStats {
  const personTotals = getPersonTotals(report, excludeBots, 1000, selectedRepo, dateRange, selectedUser, excludeOwnPR);

  const totalComments = personTotals.reduce((sum, p) => sum + p.total, 0);
  const totalPRs = personTotals.reduce((sum, p) => sum + p.prsCommented, 0);
  const totalPeople = personTotals.length;
  const averagePerPerson =
    totalPeople > 0 ? Math.round((totalComments / totalPeople) * 10) / 10 : 0;
  const avgCommentsPerPR =
    totalPRs > 0 ? Math.round((totalComments / totalPRs) * 10) / 10 : 0;

  return { totalComments, totalPeople, averagePerPerson, avgCommentsPerPR };
}

export function getActivityOverTime(
  report: CommentReport,
  excludeBots: boolean = true,
  selectedRepo: string | null = null,
  selectedUser: string | null = null,
  excludeOwnPR: boolean = false
): ActivityByDate[] {
  const activityByDate = new Map<string, { created: number; comment: number; approved: number; changes_requested: number; merged: number; closed: number }>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const prAuthor = getPRAuthor(pr);
      for (const event of pr.events) {
        if (excludeBots && isBot(event.person)) continue;
        if (!matchesUser(event.person, selectedUser)) continue;
        // For excludeOwnPR, only filter comment/approved/changes_requested (not created/merged/closed)
        if (excludeOwnPR && event.person === prAuthor && ['comment', 'approved', 'changes_requested'].includes(event.type)) continue;

        const date = event.date.split('T')[0];
        const existing = activityByDate.get(date) ?? { created: 0, comment: 0, approved: 0, changes_requested: 0, merged: 0, closed: 0 };
        existing[event.type] += 1;
        activityByDate.set(date, existing);
      }
    }
  }

  return Array.from(activityByDate.entries())
    .map(([date, counts]) => ({ date, ...counts }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export interface ReviewStatsByPerson {
  name: string;
  approved: number;
  changesRequested: number;
  total: number;
}

export function getReviewStatsByPerson(
  report: CommentReport,
  excludeBots: boolean = true,
  limit: number = 15,
  selectedRepo: string | null = null,
  dateRange: FilterDateRange | null = null,
  selectedUser: string | null = null,
  excludeOwnPR: boolean = false
): ReviewStatsByPerson[] {
  // Track unique reviews per person per PR (person -> { approved PRs, changes_requested PRs })
  const reviewStats = new Map<string, { approvedPRs: Set<string>; changesRequestedPRs: Set<string> }>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const prKey = `${repo}#${pr.number}`;
      const prAuthor = getPRAuthor(pr);
      for (const event of pr.events) {
        if (event.type !== 'approved' && event.type !== 'changes_requested') continue;
        if (excludeBots && isBot(event.person)) continue;
        if (!isInDateRange(event.date, dateRange)) continue;
        if (!matchesUser(event.person, selectedUser)) continue;
        if (excludeOwnPR && event.person === prAuthor) continue;

        const stats = reviewStats.get(event.person) ?? { approvedPRs: new Set(), changesRequestedPRs: new Set() };
        if (event.type === 'approved') {
          stats.approvedPRs.add(prKey);
        } else {
          stats.changesRequestedPRs.add(prKey);
        }
        reviewStats.set(event.person, stats);
      }
    }
  }

  const entries = Array.from(reviewStats.entries())
    .map(([name, stats]) => ({
      name,
      approved: stats.approvedPRs.size,
      changesRequested: stats.changesRequestedPRs.size,
      total: stats.approvedPRs.size + stats.changesRequestedPRs.size,
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, limit);

  return entries;
}
