import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, Bell, Library, LogIn, Plus, Rss, X } from 'lucide-react';
import {
  createJob,
  createSource,
  deleteSource,
  getNoteStats,
  getSession,
  listJobs,
  listNotes,
  listSources,
  openLogin,
  updateSource,
  verifySession,
} from './lib/api';
import type { CrawlerSession, CrawlJob, CrawlMode, Note, NoteFilters, NoteStats, Source, SourceType } from './types/api';
import { JobsPage } from './components/JobsPage';
import { NewJobDialog } from './components/NewJobDialog';
import { NoteDetail } from './components/NoteDetail';
import { NotesPage } from './components/NotesPage';
import { SessionPage } from './components/SessionPage';
import { SourcesPage } from './components/SourcesPage';
import { statusLabel } from './lib/format';
import './styles/app.css';

type Page = 'library' | 'jobs' | 'sources' | 'session';

const initialFilters: NoteFilters = { page: 1, page_size: 18, sort: 'engagement' };
const emptyStats: NoteStats = { total_notes: 0, added_last_24h: 0, active_sources: 0, total_sources: 0 };

export default function App() {
  const [page, setPage] = useState<Page>('library');
  const [notes, setNotes] = useState<Note[]>([]);
  const [stats, setStats] = useState<NoteStats>(emptyStats);
  const [sources, setSources] = useState<Source[]>([]);
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [session, setSession] = useState<CrawlerSession | null>(null);
  const [filters, setFilters] = useState<NoteFilters>(initialFilters);
  const [noteTotal, setNoteTotal] = useState(0);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [noteView, setNoteView] = useState<'grid' | 'list'>('grid');
  const [showJobDialog, setShowJobDialog] = useState(false);
  const [loadingNotes, setLoadingNotes] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasRunningJob = useMemo(() => jobs.some((job) => ['pending', 'running'].includes(job.status)), [jobs]);
  const sessionBusy = session?.status === 'login_running' || session?.status === 'verifying';

  async function refreshNotes(nextFilters = filters) {
    setLoadingNotes(true);
    try {
      const result = await listNotes(nextFilters);
      setNotes(result.items); setNoteTotal(result.total);
    } catch (err) { reportError(err); }
    finally { setLoadingNotes(false); }
  }

  async function refreshOverview() {
    const results = await Promise.allSettled([getNoteStats(), listSources(), listJobs(), getSession()]);
    if (results[0].status === 'fulfilled') setStats(results[0].value);
    if (results[1].status === 'fulfilled') setSources(results[1].value);
    if (results[2].status === 'fulfilled') setJobs(results[2].value);
    if (results[3].status === 'fulfilled') setSession(results[3].value);
    const failed = results.find((result) => result.status === 'rejected');
    if (failed?.status === 'rejected') reportError(failed.reason);
  }

  useEffect(() => { void refreshOverview(); }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void refreshNotes(filters), 220);
    return () => window.clearTimeout(timer);
  }, [filters]);
  useEffect(() => {
    if (!hasRunningJob && !sessionBusy) return;
    const timer = window.setInterval(() => void refreshOverview(), 3500);
    return () => window.clearInterval(timer);
  }, [hasRunningJob, sessionBusy]);

  function reportError(value: unknown) { setError(value instanceof Error ? value.message : '操作失败，请稍后重试。'); }

  async function handleCreateSource(name: string, type: SourceType, target: string) {
    setWorking(true); setError(null);
    try { await createSource(name.trim(), type, target.trim()); setSources(await listSources()); setStats(await getNoteStats()); }
    catch (err) { reportError(err); throw err; }
    finally { setWorking(false); }
  }

  async function handleToggleSource(source: Source) {
    try { await updateSource(source.id, !source.enabled); setSources(await listSources()); setStats(await getNoteStats()); }
    catch (err) { reportError(err); }
  }

  async function handleDeleteSource(source: Source) {
    if (!window.confirm(`确定删除信源“${source.name}”吗？已采集的笔记会保留。`)) return;
    try { await deleteSource(source.id); setSources(await listSources()); setStats(await getNoteStats()); }
    catch (err) { reportError(err); }
  }

  async function handleCreateJob(sourceIds: number[], maxNotes: number, crawlMode: CrawlMode) {
    setWorking(true); setError(null);
    try { await createJob(sourceIds, maxNotes, crawlMode); setJobs(await listJobs()); setShowJobDialog(false); setPage('jobs'); }
    catch (err) { reportError(err); }
    finally { setWorking(false); }
  }

  async function handleVerifySession() {
    setWorking(true); setError(null);
    try { setSession(await verifySession()); }
    catch (err) { reportError(err); }
    finally { setWorking(false); }
  }

  async function handleOpenLogin() {
    setWorking(true); setError(null);
    try { setSession(await openLogin()); }
    catch (err) { reportError(err); }
    finally { setWorking(false); }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">R</span><div><strong>RedScope</strong><small>小红书内容研究台</small></div></div>
        <div className="top-actions">
          <button className={`session-health status-${session?.status ?? 'public'}`} onClick={() => setPage('session')}><span />{session?.status === 'active' ? '登录模式' : sessionBusy ? (statusLabel[session?.status ?? ''] ?? '处理中') : '匿名模式'}</button>
          <button className="icon-button" title="任务通知" aria-label="任务通知" onClick={() => setPage('jobs')}><Bell size={18} /></button>
          <button className="primary-button" onClick={() => setShowJobDialog(true)}><Plus size={17} />新建采集</button>
        </div>
      </header>
      {error ? <div className="error-banner" role="alert"><AlertCircle size={18} /><span>{error}</span><button aria-label="关闭错误提示" title="关闭" onClick={() => setError(null)}><X size={17} /></button></div> : null}
      <div className="workspace">
        <nav className="sidebar" aria-label="主导航">
          <NavButton active={page === 'library'} icon={<Library size={18} />} label="笔记库" onClick={() => setPage('library')} />
          <NavButton active={page === 'jobs'} icon={<Activity size={18} />} label="采集任务" onClick={() => setPage('jobs')} />
          <NavButton active={page === 'sources'} icon={<Rss size={18} />} label="信源管理" onClick={() => setPage('sources')} />
          <span className="nav-section-label">运维</span>
          <NavButton active={page === 'session'} icon={<LogIn size={18} />} label="登录会话" onClick={() => setPage('session')} />
        </nav>
        <main className="main-content">
          {page === 'library' ? <NotesPage notes={notes} stats={stats} sources={sources} total={noteTotal} loading={loadingNotes} filters={filters} view={noteView} onFiltersChange={setFilters} onViewChange={setNoteView} onSelect={setSelectedNote} /> : null}
          {page === 'jobs' ? <JobsPage jobs={jobs} loading={working} onRefresh={() => void refreshOverview()} /> : null}
          {page === 'sources' ? <SourcesPage sources={sources} onCreate={handleCreateSource} onToggle={handleToggleSource} onDelete={handleDeleteSource} /> : null}
          {page === 'session' ? <SessionPage session={session} loading={working} onVerify={handleVerifySession} onLogin={handleOpenLogin} /> : null}
        </main>
      </div>
      <NoteDetail note={selectedNote} sources={sources} onClose={() => setSelectedNote(null)} />
      <NewJobDialog open={showJobDialog} sources={sources} loading={working} onClose={() => setShowJobDialog(false)} onCreate={handleCreateJob} onGoSources={() => { setShowJobDialog(false); setPage('sources'); }} />
    </div>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return <button className={active ? 'active' : ''} aria-current={active ? 'page' : undefined} onClick={onClick}>{icon}<span>{label}</span></button>;
}
