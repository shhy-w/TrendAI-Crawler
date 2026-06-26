import { Play, RefreshCw } from 'lucide-react';
import type { CrawlJob } from '../types/api';

type CrawlPanelProps = {
  keywords: string;
  maxPosts: number;
  jobs: CrawlJob[];
  loading: boolean;
  onKeywordsChange: (value: string) => void;
  onMaxPostsChange: (value: number) => void;
  onCreateJob: () => void;
  onRefreshJobs: () => void;
};

export function CrawlPanel({
  keywords,
  maxPosts,
  jobs,
  loading,
  onKeywordsChange,
  onMaxPostsChange,
  onCreateJob,
  onRefreshJobs,
}: CrawlPanelProps) {
  return (
    <section className="panel crawl-panel">
      <div className="panel-title">
        <h2>采集控制</h2>
        <button className="icon-button" onClick={onRefreshJobs} title="刷新任务">
          <RefreshCw size={18} />
        </button>
      </div>
      <div className="form-grid">
        <label>
          关键词
          <input value={keywords} onChange={(event) => onKeywordsChange(event.target.value)} />
        </label>
        <label>
          单词条上限
          <input
            type="number"
            min={1}
            max={100}
            value={maxPosts}
            onChange={(event) => onMaxPostsChange(Number(event.target.value))}
          />
        </label>
        <button className="primary-button" onClick={onCreateJob} disabled={loading}>
          <Play size={17} />
          触发采集
        </button>
      </div>
      <div className="job-list">
        {jobs.length === 0 ? (
          <p className="muted">暂无任务</p>
        ) : (
          jobs.slice(0, 5).map((job) => (
            <div className="job-item" key={job.id}>
              <span className={`status status-${job.status}`}>{job.status}</span>
              <span className="job-keywords">{job.keywords.join(', ')}</span>
              <span>{job.success_count} 条</span>
              {job.failure_type ? <span className="failure-type">{job.failure_type}</span> : null}
              {job.error_message ? <span className="error-text">{job.error_message}</span> : null}
              {job.debug_path ? <span className="debug-path">{job.debug_path}</span> : null}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
