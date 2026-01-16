import type { CommentReport, PersonTotal, PRMergedByPerson, RepoPRCounts, ActivityByDate } from '../types';

export function isBot(name: string): boolean {
  return name.endsWith('[bot]') || name === 'Copilot';
}

export function getPersonTotals(
  report: CommentReport,
  excludeBots: boolean = true,
  limit: number = 15,
  selectedRepo: string | null = null
): PersonTotal[] {
  const personStats = new Map<string, { comments: number; prs: Set<string> }>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      for (const event of pr.events) {
        if (event.type !== 'comment') continue;
        if (excludeBots && isBot(event.person)) continue;

        const prKey = `${repo}#${pr.number}`;
        const stats = personStats.get(event.person) ?? { comments: 0, prs: new Set() };
        stats.comments += 1;
        stats.prs.add(prKey);
        personStats.set(event.person, stats);
      }
    }
  }

  const entries = Array.from(personStats.entries())
    .map(([name, stats]) => ({
      name,
      total: stats.comments,
      prsCommented: stats.prs.size,
      avgPerPR: stats.prs.size > 0 ? Math.round((stats.comments / stats.prs.size) * 10) / 10 : 0,
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, limit);

  return entries;
}

export function getPRMergedByPerson(
  report: CommentReport,
  excludeBots: boolean = true,
  limit: number = 15,
  selectedRepo: string | null = null
): PRMergedByPerson[] {
  const mergedCounts = new Map<string, number>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const mergedEvent = pr.events.find(e => e.type === 'merged');
      if (mergedEvent) {
        if (excludeBots && isBot(mergedEvent.person)) continue;
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
  selectedRepo: string | null = null
): PRCreatedByPerson[] {
  const createdCounts = new Map<string, number>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      const createdEvent = pr.events.find(e => e.type === 'created');
      if (createdEvent) {
        if (excludeBots && isBot(createdEvent.person)) continue;
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
  selectedRepo: string | null = null
): { repo: string; counts: RepoPRCounts }[] {
  const repoCounts: { repo: string; counts: RepoPRCounts }[] = [];

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    let open = 0;
    let merged = 0;
    let closed = 0;

    for (const pr of prs) {
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

    repoCounts.push({ repo, counts: { open, merged, closed } });
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
  avgTimeToClose: number | null;    // hours
}

export function getRepoTimeStats(
  report: CommentReport,
  selectedRepo: string | null = null
): RepoTimeStats[] {
  const stats: RepoTimeStats[] = [];

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    const timeToComments: number[] = [];
    const timeToClose: number[] = [];

    for (const pr of prs) {
      const createdEvent = pr.events.find(e => e.type === 'created');
      if (!createdEvent) continue;

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
    const avgClose = timeToClose.length > 0
      ? Math.round((timeToClose.reduce((a, b) => a + b, 0) / timeToClose.length) * 10) / 10
      : null;

    stats.push({ repo, avgTimeToComment: avgComment, avgTimeToClose: avgClose });
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
  selectedRepo: string | null = null
): AverageStats {
  const personTotals = getPersonTotals(report, excludeBots, 1000, selectedRepo);

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
  selectedRepo: string | null = null
): ActivityByDate[] {
  const activityByDate = new Map<string, { created: number; comment: number; merged: number; closed: number }>();

  for (const [repo, prs] of Object.entries(report.repositories)) {
    if (selectedRepo && repo !== selectedRepo) continue;
    for (const pr of prs) {
      for (const event of pr.events) {
        if (excludeBots && isBot(event.person)) continue;

        const date = event.date.split('T')[0];
        const existing = activityByDate.get(date) ?? { created: 0, comment: 0, merged: 0, closed: 0 };
        existing[event.type] += 1;
        activityByDate.set(date, existing);
      }
    }
  }

  return Array.from(activityByDate.entries())
    .map(([date, counts]) => ({ date, ...counts }))
    .sort((a, b) => a.date.localeCompare(b.date));
}
