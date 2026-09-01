import { Bookmark, ExternalLink, Heart, MapPin, MessageCircle, Share2, X } from 'lucide-react';
import type { Note, Source } from '../types/api';
import { compactNumber, formatDate } from '../lib/format';

export function NoteDetail({ note, sources, onClose }: { note: Note | null; sources: Source[]; onClose: () => void }) {
  if (!note) return null;
  const sourceNames = note.source_links.map((link) => sources.find((source) => source.id === link.source_id)?.name).filter(Boolean);
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <article className="detail-drawer" onMouseDown={(event) => event.stopPropagation()}>
        <header className="detail-header"><div><span className="eyebrow">{note.note_type === 'video' ? '视频笔记' : '图文笔记'}</span><h2>{note.title || '未命名笔记'}</h2></div><button className="icon-button" onClick={onClose} title="关闭" aria-label="关闭"><X size={19} /></button></header>
        <div className="detail-author"><span className="avatar large">{note.author_avatar ? <img src={note.author_avatar} alt="" referrerPolicy="no-referrer" /> : (note.author_name?.slice(0, 1) ?? '匿')}</span><div><strong>{note.author_name ?? '未知作者'}</strong><span>{formatDate(note.published_at, '发布时间未知')}{note.ip_location ? ` · ${note.ip_location}` : ''}</span></div></div>
        {note.media_items.length ? <div className="detail-media">{note.media_items.map((media) => media.media_type === 'video' ? <video key={media.id} src={media.media_url} poster={media.thumbnail_url ?? undefined} controls /> : <img key={media.id} src={media.thumbnail_url ?? media.media_url} alt="" referrerPolicy="no-referrer" />)}</div> : null}
        <p className="detail-content">{note.content || '该笔记暂未补全正文。'}</p>
        <div className="detail-metrics"><span><Heart size={16} />{compactNumber(note.like_count)} 点赞</span><span><Bookmark size={16} />{compactNumber(note.collect_count)} 收藏</span><span><MessageCircle size={16} />{compactNumber(note.comment_count)} 评论</span><span><Share2 size={16} />{compactNumber(note.share_count)} 分享</span></div>
        <div className="detail-context"><div><span>命中信源</span><strong>{sourceNames.length ? sourceNames.join('、') : '直接采集'}</strong></div><div><span>最近采集</span><strong>{formatDate(note.crawled_at)}</strong></div></div>
        <footer className="detail-footer"><span><MapPin size={15} />{note.ip_location ?? '未提供 IP 属地'}</span><a className="primary-button" href={note.note_url} target="_blank" rel="noreferrer"><ExternalLink size={16} />查看原笔记</a></footer>
      </article>
    </div>
  );
}
