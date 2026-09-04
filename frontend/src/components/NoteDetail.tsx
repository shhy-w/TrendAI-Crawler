import { Archive, Bookmark, ExternalLink, Heart, Image as ImageIcon, MapPin, MessageCircle, RefreshCw, Share2, Video, X } from 'lucide-react';
import type { MediaItem, Note, Source } from '../types/api';
import { resolveApiUrl } from '../lib/api';
import { compactNumber, completenessLabel, formatDate } from '../lib/format';

type Props = {
  note: Note | null;
  sources: Source[];
  sessionActive: boolean;
  working: boolean;
  onClose: () => void;
  onArchive: (note: Note) => Promise<void>;
  onEnrich: (note: Note) => Promise<void>;
};

export function NoteDetail({ note, sources, sessionActive, working, onClose, onArchive, onEnrich }: Props) {
  if (!note) return null;
  const sourceNames = note.source_links.map((link) => sources.find((source) => source.id === link.source_id)?.name).filter(Boolean);
  const hasRemoteMedia = note.media_items.some((media) => media.archive_status !== 'archived');
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <article className="detail-drawer media-detail-drawer" onMouseDown={(event) => event.stopPropagation()}>
        <header className="detail-header">
          <div><span className="eyebrow">{note.note_type === 'video' ? '视频笔记' : '图文笔记'} · {completenessLabel[note.completeness] ?? note.completeness}</span><h2>{note.title || '未命名笔记'}</h2></div>
          <button className="icon-button" onClick={onClose} title="关闭" aria-label="关闭"><X size={19} /></button>
        </header>
        <div className="detail-author"><span className="avatar large">{note.author_avatar ? <img src={note.author_avatar} alt="" referrerPolicy="no-referrer" /> : (note.author_name?.slice(0, 1) ?? '匿')}</span><div><strong>{note.author_name ?? '未知作者'}</strong><span>{formatDate(note.published_at, '发布时间未知')}{note.ip_location ? ` · ${note.ip_location}` : ''}</span></div></div>
        {note.media_items.length ? <div className="detail-media">{note.media_items.map((media) => <MediaViewer media={media} key={media.id} />)}</div> : <div className="media-empty"><ImageIcon size={26} /><span>暂无媒体资源</span></div>}
        <div className="media-actions">
          <button className="secondary-button" disabled={working || !hasRemoteMedia} onClick={() => void onArchive(note)}><Archive size={16} />{working ? '处理中...' : hasRemoteMedia ? '归档当前媒体' : '媒体已归档'}</button>
          <button className="primary-button" disabled={working || !sessionActive} title={sessionActive ? '获取笔记详情媒体' : '需要可用的登录会话'} onClick={() => void onEnrich(note)}><RefreshCw size={16} />补全原图与视频</button>
        </div>
        <p className="detail-content">{note.content || '该笔记暂未补全正文。'}</p>
        <div className="detail-metrics"><span><Heart size={16} />{compactNumber(note.like_count)} 点赞</span><span><Bookmark size={16} />{compactNumber(note.collect_count)} 收藏</span><span><MessageCircle size={16} />{compactNumber(note.comment_count)} 评论</span><span><Share2 size={16} />{compactNumber(note.share_count)} 分享</span></div>
        <div className="detail-context"><div><span>命中信源</span><strong>{sourceNames.length ? sourceNames.join('、') : '直接采集'}</strong></div><div><span>最近采集</span><strong>{formatDate(note.crawled_at)}</strong></div></div>
        <footer className="detail-footer"><span><MapPin size={15} />{note.ip_location ?? '未提供 IP 属地'}</span><a className="primary-button" href={note.note_url} target="_blank" rel="noreferrer"><ExternalLink size={16} />查看原笔记</a></footer>
      </article>
    </div>
  );
}

function MediaViewer({ media }: { media: MediaItem }) {
  const contentUrl = resolveApiUrl(media.content_url);
  const poster = media.thumbnail_url ? resolveApiUrl(media.thumbnail_url) : undefined;
  return (
    <figure className="media-viewer">
      <div className="media-stage">
        {media.media_type === 'video' ? <video src={contentUrl} poster={poster} controls preload="metadata" playsInline /> : <img src={contentUrl} alt="" referrerPolicy="no-referrer" />}
      </div>
      <figcaption>
        <span>{media.media_type === 'video' ? <Video size={14} /> : <ImageIcon size={14} />}{qualityLabel(media.quality)}</span>
        <span>{media.width && media.height ? `${media.width} × ${media.height}` : '尺寸待归档'}</span>
        <span>{media.file_size ? formatBytes(media.file_size) : media.archive_status === 'failed' ? '归档失败' : media.archive_status === 'archived' ? '已归档' : '远程资源'}</span>
      </figcaption>
      {media.archive_error ? <p className="media-error">{media.archive_error}</p> : null}
    </figure>
  );
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${bytes} B`;
}

function qualityLabel(quality: string): string {
  if (quality === 'original') return '高分辨率图片';
  if (quality === 'detail') return '详情图片';
  if (quality === 'playback') return '可播放视频';
  return '预览资源';
}
