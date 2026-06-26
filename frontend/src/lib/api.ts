import type { CrawlJob, Post, PostFilters, PostListResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function listPosts(filters: PostFilters): Promise<PostListResponse> {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.page_size),
    sort: filters.sort,
  });
  if (filters.keyword) params.set('keyword', filters.keyword);
  if (filters.author) params.set('author', filters.author);
  if (filters.has_media !== undefined) params.set('has_media', String(filters.has_media));
  return request<PostListResponse>(`/api/posts?${params.toString()}`);
}

export function getPost(id: number): Promise<Post> {
  return request<Post>(`/api/posts/${id}`);
}

export function listJobs(): Promise<CrawlJob[]> {
  return request<CrawlJob[]>('/api/crawl-jobs');
}

export function createJob(keywords: string[], maxPostsPerKeyword: number): Promise<CrawlJob> {
  return request<CrawlJob>('/api/crawl-jobs', {
    method: 'POST',
    body: JSON.stringify({
      keywords,
      max_posts_per_keyword: maxPostsPerKeyword,
    }),
  });
}
