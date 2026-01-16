export type EventType = "created" | "comment" | "merged" | "closed";

export interface PREvent {
  type: EventType;
  date: string;
  person: string;
}

export interface PRRecord {
  number: number;
  title: string;
  events: PREvent[];
}

export interface DateRange {
  since: string | null;
  until: string | null;
}

export interface CommentReport {
  organization: string;
  generated_at: string;
  date_range: DateRange;
  repositories: Record<string, PRRecord[]>;
}

export interface PersonTotal {
  name: string;
  total: number;
  prsCommented: number;
  avgPerPR: number;
  stdDevPerPR: number;
}

export interface PRMergedByPerson {
  name: string;
  merged: number;
}

export interface PRCreatedByPerson {
  name: string;
  created: number;
}

export interface RepoPRCounts {
  open: number;
  merged: number;
  closed: number;
}

export interface ActivityByDate {
  date: string;
  created: number;
  comment: number;
  merged: number;
  closed: number;
}

export interface FilterDateRange {
  start: string | null;
  end: string | null;
}
