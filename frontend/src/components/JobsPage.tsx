import { Activity, AlertCircle, CheckCircle2, Clock3 } from 'lucide-react';
import type { CrawlJob } from '../types/api';
import { crawlModeLabel, formatDate, sourceTypeLabel, statusLabel } from '../lib/format';

export function JobsPage({ jobs, loading, onRefresh }: { jobs: CrawlJob[]; loading: boolean; onRefresh: () => void }) {
  return (
    <section className="page-section">
      <div className="page-heading"><div><h1>采集任务</h1><p>查看每个信源的进度、增量结果和失败原因</p></div><button className="secondary-button" onClick={onRefresh} disabled={loading}>刷新状态</button></div>
      {jobs.length === 0 ? <div className="empty-state"><Activity size={28} /><strong>暂无采集任务</strong><span>从右上角新建一次采集，任务进度会显示在这里。</span></div> : null}
      <div className="job-stack">
        {jobs.map((job) => {
          const progress = job.total_sources ? Math.round(job.completed_sources / job.total_sources * 100) : 0;
          return <article className="job-record" key={job.id}>
            <header><div className="job-title"><StatusIcon status={job.status} /><div><strong>任务 #{job.id}</strong><span>{formatDate(job.created_at)} · {crawlModeLabel[job.crawl_mode]} · 每个信源最多 {job.max_notes_per_source} 条</span></div></div><span className={`status status-${job.status}`}>{statusLabel[job.status] ?? job.status}</span></header>
            <div className="job-summary"><div><span>进度</span><strong>{job.completed_sources} / {job.total_sources}</strong></div><div><span>发现</span><strong>{job.discovered_count}</strong></div><div><span>已写入</span><strong>{job.success_count}</strong></div><div className="progress-wrap"><span>{progress}%</span><div className="progress"><i style={{ width: `${progress}%` }} /></div></div></div>
            <div className="table-wrap"><table><thead><tr><th>信源</th><th>类型</th><th>状态</th><th>发现 / 写入</th><th>结果</th></tr></thead><tbody>{job.items.map((item) => <tr key={item.id}><td><strong>{item.source_name}</strong></td><td>{sourceTypeLabel[item.source_type] ?? item.source_type}</td><td><span className={`status status-${item.status}`}>{statusLabel[item.status] ?? item.status}</span></td><td>{item.discovered_count} / {item.saved_count}</td><td className={item.error_message ? 'error-text' : 'muted'}>{item.error_message ?? formatDate(item.finished_at, '等待执行')}</td></tr>)}</tbody></table></div>
          </article>;
        })}
      </div>
    </section>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'succeeded') return <CheckCircle2 className="success-icon" size={20} />;
  if (status === 'failed' || status === 'partial') return <AlertCircle className="warning-icon" size={20} />;
  return <Clock3 className="running-icon" size={20} />;
}
