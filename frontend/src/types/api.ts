export type MediaItem = {
  id: number;
  media_type: 'image' | 'video' | string;
  media_url: string;
  thumbnail_url: string | null;
  width: number | null;
  height: number | null;
  sort_order: number;
};

export type NoteSourceLink = {
  source_id: number;
  discovered_at: string;
  last_seen_at: string;
};

export type Note = {
  id: number;
  platform_note_id: string;
  note_type: string;
  completeness: 'card' | 'partial' | 'complete' | string;
  title: string;
  content: string;
  author_id: string | null;
  author_name: string | null;
  author_avatar: string | null;
  published_at: string | null;
  ip_location: string | null;
  note_url: string;
  like_count: number;
  collect_count: number;
  comment_count: number;
  share_count: number;
  crawled_at: string;
  media_items: MediaItem[];
  source_links: NoteSourceLink[];
};

export type NoteListResponse = {
  items: Note[];
  total: number;
  page: number;
  page_size: number;
};

export type NoteStats = {
  total_notes: number;
  added_last_24h: number;
  active_sources: number;
  total_sources: number;
};

export type SourceType = 'explore' | 'keyword' | 'profile' | 'note';

export type Source = {
  id: number;
  name: string;
  source_type: SourceType;
  target: string;
  enabled: boolean;
  public_supported: boolean;
  last_run_at: string | null;
  last_success_at: string | null;
  last_result_count: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type CrawlJobItem = {
  id: number;
  source_id: number | null;
  source_name: string;
  source_type: string;
  target: string;
  status: string;
  discovered_count: number;
  saved_count: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type CrawlJob = {
  id: number;
  status: string;
  crawl_mode: CrawlMode;
  max_notes_per_source: number;
  total_sources: number;
  completed_sources: number;
  discovered_count: number;
  started_at: string | null;
  finished_at: string | null;
  success_count: number;
  failure_type: string | null;
  debug_path: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  items: CrawlJobItem[];
};

export type CrawlMode = 'auto' | 'public' | 'authenticated';

export type CrawlerSession = {
  id: number;
  name: string;
  status: string;
  last_verified_at: string | null;
  last_error: string | null;
  protection_enabled: boolean;
  daily_request_limit: number;
  daily_request_count: number;
  daily_request_date: string | null;
  cooldown_seconds: number;
  failure_threshold: number;
  lockout_minutes: number;
  consecutive_failures: number;
  last_request_at: string | null;
  blocked_until: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountProtectionSettings = Pick<
  CrawlerSession,
  'protection_enabled' | 'daily_request_limit' | 'cooldown_seconds' | 'failure_threshold' | 'lockout_minutes'
>;

export type NoteFilters = {
  page: number;
  page_size: number;
  query?: string;
  author?: string;
  source_id?: number;
  note_type?: string;
  has_media?: boolean;
  sort: 'engagement' | 'published_at' | 'crawled_at';
};
