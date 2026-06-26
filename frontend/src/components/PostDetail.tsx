import { ExternalLink, X } from 'lucide-react';
import type { Post } from '../types/api';

type PostDetailProps = {
  post: Post | null;
  onClose: () => void;
};

export function PostDetail({ post, onClose }: PostDetailProps) {
  if (!post) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <article className="detail-modal" onClick={(event) => event.stopPropagation()}>
        <div className="detail-header">
          <div>
            <h2>{post.author_name ?? 'Unknown'}</h2>
            {post.author_handle ? <span>@{post.author_handle}</span> : null}
          </div>
          <button className="icon-button" onClick={onClose} title="关闭">
            <X size={18} />
          </button>
        </div>
        <p className="detail-text">{post.text}</p>
        {post.media_items.length > 0 ? (
          <div className="media-grid">
            {post.media_items.map((media) => (
              <a href={media.media_url} target="_blank" rel="noreferrer" className="media-item" key={media.id}>
                {media.media_type === 'video' ? (
                  <video src={media.media_url} poster={media.thumbnail_url ?? undefined} controls />
                ) : (
                  <img src={media.thumbnail_url ?? media.media_url} alt="" />
                )}
              </a>
            ))}
          </div>
        ) : null}
        <div className="detail-footer">
          <span>{post.published_at ? new Date(post.published_at).toLocaleString() : '发布时间未知'}</span>
          <a className="primary-link" href={post.post_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} />
            查看原文
          </a>
        </div>
      </article>
    </div>
  );
}
