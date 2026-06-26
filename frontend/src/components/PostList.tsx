import { ExternalLink, Image as ImageIcon, MessageCircle, Repeat2, ThumbsUp } from 'lucide-react';
import type { Post } from '../types/api';

type PostListProps = {
  posts: Post[];
  loading: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onSelectPost: (post: Post) => void;
};

export function PostList({ posts, loading, total, page, pageSize, onPageChange, onSelectPost }: PostListProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <section className="post-section">
      <div className="section-header">
        <h2>内容列表</h2>
        <span>{total} 条</span>
      </div>
      {loading ? <div className="empty-state">加载中...</div> : null}
      {!loading && posts.length === 0 ? <div className="empty-state">暂无内容，先触发一次采集。</div> : null}
      <div className="post-list">
        {posts.map((post) => (
          <article className="post-card" key={post.id} onClick={() => onSelectPost(post)}>
            <div className="post-card-main">
              <div className="post-meta">
                <strong>{post.author_name ?? 'Unknown'}</strong>
                {post.author_handle ? <span>@{post.author_handle}</span> : null}
                <span>{post.keyword}</span>
              </div>
              <p>{post.text}</p>
              <div className="metrics">
                <span>
                  <MessageCircle size={15} />
                  {post.reply_count}
                </span>
                <span>
                  <Repeat2 size={15} />
                  {post.repost_count}
                </span>
                <span>
                  <ThumbsUp size={15} />
                  {post.like_count}
                </span>
                {post.media_items.length > 0 ? (
                  <span>
                    <ImageIcon size={15} />
                    {post.media_items.length}
                  </span>
                ) : null}
              </div>
            </div>
            <a href={post.post_url} target="_blank" rel="noreferrer" className="icon-button" onClick={(event) => event.stopPropagation()}>
              <ExternalLink size={17} />
            </a>
          </article>
        ))}
      </div>
      <div className="pagination">
        <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          上一页
        </button>
        <span>
          {page} / {totalPages}
        </span>
        <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          下一页
        </button>
      </div>
    </section>
  );
}
