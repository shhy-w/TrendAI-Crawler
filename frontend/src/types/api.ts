export type MediaItem = {
  id: number;
  media_type: 'image' | 'video' | string;
  media_url: string;
  thumbnail_url: string | null;
  width: number | null;
  height: number | null;
  sort_order: number;
};

export type Post = {
  id: number;
  x_post_id: string;
  keyword: string;
  text: string;
  author_name: string | null;
  author_handle: string | null;
  published_at: string | null;
  post_url: string;
  reply_count: number;
  repost_count: number;
  like_count: number;
  view_count: number;
  crawled_at: string;
  media_items: MediaItem[];
};

export type PostListResponse = {
  items: Post[];
  total: number;
  page: number;
  page_size: number;
};

export type CrawlJob = {
  id: number;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | string;
  keywords: string[];
  max_posts_per_keyword: number;
  started_at: string | null;
  finished_at: string | null;
  success_count: number;
  failure_type: string | null;
  debug_path: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ProxyItem = {
  id: number;
  name: string;
  proxy_url: string;
  status: string;
  failure_count: number;
  success_count: number;
  last_error: string | null;
  last_checked_at: string | null;
  cooldown_until: string | null;
  created_at: string;
  updated_at: string;
};

export type ProxyCheckResult = {
  proxy_id: number;
  status: string;
  message: string;
  guest_token_ok: boolean;
};

export type PostFilters = {
  page: number;
  page_size: number;
  keyword?: string;
  author?: string;
  has_media?: boolean;
  sort: 'hot' | 'published_at' | 'crawled_at';
};
