import { useEffect, useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { createJob, listJobs, listPosts } from './lib/api';
import type { CrawlJob, Post, PostFilters } from './types/api';
import { CrawlPanel } from './components/CrawlPanel';
import { Filters } from './components/Filters';
import { PostDetail } from './components/PostDetail';
import { PostList } from './components/PostList';
import './styles/app.css';

const initialFilters: PostFilters = {
  page: 1,
  page_size: 20,
  sort: 'hot',
};

export default function App() {
  const [filters, setFilters] = useState<PostFilters>(initialFilters);
  const [posts, setPosts] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [keywords, setKeywords] = useState('AI, vibe coding, agent');
  const [maxPosts, setMaxPosts] = useState(20);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [creatingJob, setCreatingJob] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasRunningJob = useMemo(() => jobs.some((job) => job.status === 'pending' || job.status === 'running'), [jobs]);

  async function refreshPosts(nextFilters = filters) {
    setLoadingPosts(true);
    setError(null);
    try {
      const response = await listPosts(nextFilters);
      setPosts(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载内容失败');
    } finally {
      setLoadingPosts(false);
    }
  }

  async function refreshJobs() {
    try {
      setJobs(await listJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载任务失败');
    }
  }

  async function handleCreateJob() {
    const parsedKeywords = keywords
      .split(',')
      .map((keyword) => keyword.trim())
      .filter(Boolean);
    if (parsedKeywords.length === 0) {
      setError('至少需要一个关键词');
      return;
    }
    setCreatingJob(true);
    setError(null);
    try {
      await createJob(parsedKeywords, maxPosts);
      await refreshJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建采集任务失败');
    } finally {
      setCreatingJob(false);
    }
  }

  function handleFiltersChange(nextFilters: PostFilters) {
    setFilters(nextFilters);
    void refreshPosts(nextFilters);
  }

  useEffect(() => {
    void refreshPosts();
    void refreshJobs();
  }, []);

  useEffect(() => {
    if (!hasRunningJob) return;
    const timer = window.setInterval(() => {
      void refreshJobs();
      void refreshPosts();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [hasRunningJob, filters]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>TrendAI Crawler</h1>
          <p>X 热门 AI 内容采集与查看</p>
        </div>
      </header>

      {error ? (
        <div className="error-banner">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="workspace">
        <aside className="sidebar">
          <CrawlPanel
            keywords={keywords}
            maxPosts={maxPosts}
            jobs={jobs}
            loading={creatingJob}
            onKeywordsChange={setKeywords}
            onMaxPostsChange={setMaxPosts}
            onCreateJob={handleCreateJob}
            onRefreshJobs={refreshJobs}
          />
        </aside>
        <section className="content">
          <Filters filters={filters} onChange={handleFiltersChange} />
          <PostList
            posts={posts}
            loading={loadingPosts}
            total={total}
            page={filters.page}
            pageSize={filters.page_size}
            onPageChange={(page) => handleFiltersChange({ ...filters, page })}
            onSelectPost={setSelectedPost}
          />
        </section>
      </div>
      <PostDetail post={selectedPost} onClose={() => setSelectedPost(null)} />
    </main>
  );
}
