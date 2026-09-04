import { Bookmark, Grid2X2, Heart, Image as ImageIcon, List, MessageCircle, Search, Share2 } from 'lucide-react';
import type { Note, NoteFilters, NoteStats, Source } from '../types/api';
import { compactNumber, completenessLabel } from '../lib/format';
import { resolveApiUrl } from '../lib/api';

type Props = {
  notes: Note[];
  stats: NoteStats;
  sources: Source[];
  total: number;
  loading: boolean;
  filters: NoteFilters;
  view: 'grid' | 'list';
  onFiltersChange: (filters: NoteFilters) => void;
  onViewChange: (view: 'grid' | 'list') => void;
  onSelect: (note: Note) => void;
};

export function NotesPage({ notes, stats, sources, total, loading, filters, view, onFiltersChange, onViewChange, onSelect }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / filters.page_size));
  return (
    <section className="page-section">
      <div className="page-heading">
        <div><h1>笔记库</h1><p>检索、筛选并沉淀可复用的小红书内容样本</p></div>
      </div>

      <div className="stats-band">
        <div><span>累计笔记</span><strong>{compactNumber(stats.total_notes)}</strong></div>
        <div><span>24 小时新增</span><strong>+{compactNumber(stats.added_last_24h)}</strong></div>
        <div><span>活跃信源</span><strong>{stats.active_sources} / {stats.total_sources}</strong></div>
      </div>

      <div className="filter-toolbar">
        <label className="search-field">
          <Search size={17} aria-hidden="true" />
          <span className="sr-only">搜索笔记</span>
          <input
            placeholder="搜索标题或正文"
            value={filters.query ?? ''}
            onChange={(event) => onFiltersChange({ ...filters, page: 1, query: event.target.value || undefined })}
          />
        </label>
        <select
          aria-label="按信源筛选"
          value={filters.source_id ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, page: 1, source_id: event.target.value ? Number(event.target.value) : undefined })}
        >
          <option value="">全部信源</option>
          {sources.map((source) => <option value={source.id} key={source.id}>{source.name}</option>)}
        </select>
        <select
          aria-label="按内容类型筛选"
          value={filters.note_type ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, page: 1, note_type: event.target.value || undefined })}
        >
          <option value="">全部类型</option><option value="normal">图文</option><option value="video">视频</option>
        </select>
        <select
          aria-label="排序方式"
          value={filters.sort}
          onChange={(event) => onFiltersChange({ ...filters, page: 1, sort: event.target.value as NoteFilters['sort'] })}
        >
          <option value="engagement">互动量排序</option><option value="published_at">最新发布</option><option value="crawled_at">最新采集</option>
        </select>
        <div className="segmented icon-segmented" aria-label="显示方式">
          <button type="button" aria-label="卡片视图" title="卡片视图" className={view === 'grid' ? 'active' : ''} onClick={() => onViewChange('grid')}><Grid2X2 size={17} /></button>
          <button type="button" aria-label="列表视图" title="列表视图" className={view === 'list' ? 'active' : ''} onClick={() => onViewChange('list')}><List size={18} /></button>
        </div>
      </div>

      {loading ? <div className="empty-state">正在加载笔记...</div> : null}
      {!loading && notes.length === 0 ? (
        <div className="empty-state"><ImageIcon size={28} /><strong>还没有匹配的笔记</strong><span>添加信源并运行一次采集任务后，内容会出现在这里。</span></div>
      ) : null}
      <div className={`note-collection ${view}`}>
        {notes.map((note) => {
          const media = note.media_items[0];
          const imageUrl = media ? resolveApiUrl(media.media_type === 'image' ? media.content_url : (media.thumbnail_url ?? media.media_url)) : undefined;
          return (
            <article className="note-card" key={note.id}>
              <button className="note-card-action" type="button" onClick={() => onSelect(note)}>
                <div className="note-cover">
                  <ImageIcon size={24} aria-hidden="true" />
                  {imageUrl ? <img src={imageUrl} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(event) => { event.currentTarget.style.display = 'none'; }} /> : null}
                  <span>{note.note_type === 'video' ? '视频' : `图文${note.media_items.length ? ` · ${note.media_items.length} 张` : ''}`} · {completenessLabel[note.completeness] ?? note.completeness}</span>
                </div>
                <div className="note-body">
                  <h2>{note.title || note.content.slice(0, 48) || '未命名笔记'}</h2>
                  <div className="note-author">
                    <span className="avatar">{note.author_avatar ? <img src={note.author_avatar} alt="" referrerPolicy="no-referrer" /> : (note.author_name?.slice(0, 1) ?? '匿')}</span>
                    <span>{note.author_name ?? '未知作者'}</span>
                  </div>
                  <div className="note-metrics">
                    <span><Heart size={14} />{compactNumber(note.like_count)}</span>
                    <span><Bookmark size={14} />{compactNumber(note.collect_count)}</span>
                    <span><MessageCircle size={14} />{compactNumber(note.comment_count)}</span>
                    <span><Share2 size={14} />{compactNumber(note.share_count)}</span>
                  </div>
                </div>
              </button>
            </article>
          );
        })}
      </div>

      {total > 0 ? <div className="pagination"><span>共 {total} 条</span><div><button disabled={filters.page <= 1} onClick={() => onFiltersChange({ ...filters, page: filters.page - 1 })}>上一页</button><span>{filters.page} / {totalPages}</span><button disabled={filters.page >= totalPages} onClick={() => onFiltersChange({ ...filters, page: filters.page + 1 })}>下一页</button></div></div> : null}
    </section>
  );
}
