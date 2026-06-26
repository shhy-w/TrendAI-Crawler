import { Search } from 'lucide-react';
import type { PostFilters } from '../types/api';

type FiltersProps = {
  filters: PostFilters;
  onChange: (filters: PostFilters) => void;
};

export function Filters({ filters, onChange }: FiltersProps) {
  return (
    <section className="panel filters">
      <label>
        关键词
        <input
          placeholder="AI"
          value={filters.keyword ?? ''}
          onChange={(event) => onChange({ ...filters, page: 1, keyword: event.target.value || undefined })}
        />
      </label>
      <label>
        作者
        <input
          placeholder="@handle 或名称"
          value={filters.author ?? ''}
          onChange={(event) => onChange({ ...filters, page: 1, author: event.target.value || undefined })}
        />
      </label>
      <label>
        媒体
        <select
          value={filters.has_media === undefined ? 'all' : String(filters.has_media)}
          onChange={(event) => {
            const value = event.target.value;
            onChange({
              ...filters,
              page: 1,
              has_media: value === 'all' ? undefined : value === 'true',
            });
          }}
        >
          <option value="all">全部</option>
          <option value="true">含媒体</option>
          <option value="false">无媒体</option>
        </select>
      </label>
      <label>
        排序
        <select
          value={filters.sort}
          onChange={(event) => onChange({ ...filters, page: 1, sort: event.target.value as PostFilters['sort'] })}
        >
          <option value="hot">热度</option>
          <option value="published_at">发布时间</option>
          <option value="crawled_at">抓取时间</option>
        </select>
      </label>
      <div className="filter-icon">
        <Search size={18} />
      </div>
    </section>
  );
}
