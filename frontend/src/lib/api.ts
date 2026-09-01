import type {
  CrawlerSession,
  AccountProtectionSettings,
  CrawlJob,
  CrawlMode,
  Note,
  NoteFilters,
  NoteListResponse,
  NoteStats,
  Source,
  SourceType,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      const body = await response.text();
      if (body) message = body;
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function listNotes(filters: NoteFilters): Promise<NoteListResponse> {
  const params = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.page_size),
    sort: filters.sort,
  });
  if (filters.query) params.set('query', filters.query);
  if (filters.author) params.set('author', filters.author);
  if (filters.source_id) params.set('source_id', String(filters.source_id));
  if (filters.note_type) params.set('note_type', filters.note_type);
  if (filters.has_media !== undefined) params.set('has_media', String(filters.has_media));
  return request<NoteListResponse>(`/api/notes?${params.toString()}`);
}

export const getNote = (id: number) => request<Note>(`/api/notes/${id}`);
export const getNoteStats = () => request<NoteStats>('/api/notes/stats');
export const listSources = () => request<Source[]>('/api/sources');
export const listJobs = () => request<CrawlJob[]>('/api/crawl-jobs');
export const getSession = () => request<CrawlerSession>('/api/sessions/primary');
export const verifySession = () => request<CrawlerSession>('/api/sessions/primary/verify', { method: 'POST' });
export const openLogin = () => request<CrawlerSession>('/api/sessions/primary/login', { method: 'POST' });
export const updateAccountProtection = (settings: AccountProtectionSettings) => request<CrawlerSession>('/api/sessions/primary/protection', { method: 'PATCH', body: JSON.stringify(settings) });

export function createSource(name: string, sourceType: SourceType, target: string): Promise<Source> {
  return request<Source>('/api/sources', {
    method: 'POST',
    body: JSON.stringify({ name, source_type: sourceType, target }),
  });
}

export function updateSource(id: number, enabled: boolean): Promise<Source> {
  return request<Source>(`/api/sources/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  });
}

export function deleteSource(id: number): Promise<void> {
  return request<void>(`/api/sources/${id}`, { method: 'DELETE' });
}

export function createJob(sourceIds: number[], maxNotesPerSource: number, crawlMode: CrawlMode): Promise<CrawlJob> {
  return request<CrawlJob>('/api/crawl-jobs', {
    method: 'POST',
    body: JSON.stringify({ source_ids: sourceIds, max_notes_per_source: maxNotesPerSource, crawl_mode: crawlMode }),
  });
}
