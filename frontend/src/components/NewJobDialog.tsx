import { Play, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { CrawlMode, Source } from '../types/api';
import { crawlModeLabel, sourceTypeLabel } from '../lib/format';

export function NewJobDialog({ open, sources, loading, onClose, onCreate, onGoSources }: { open: boolean; sources: Source[]; loading: boolean; onClose: () => void; onCreate: (sourceIds: number[], maxNotes: number, crawlMode: CrawlMode) => Promise<void>; onGoSources: () => void }) {
  const enabledSources = sources.filter((source) => source.enabled);
  const [selected, setSelected] = useState<number[]>([]);
  const [maxNotes, setMaxNotes] = useState(20);
  const [crawlMode, setCrawlMode] = useState<CrawlMode>('auto');
  useEffect(() => { if (open) setSelected(enabledSources.map((source) => source.id)); }, [open]);
  if (!open) return null;
  function toggle(id: number) { setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]); }
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="dialog job-dialog" onMouseDown={(event) => event.stopPropagation()}><header><div><h2>新建采集</h2><p>本次任务会按所选信源逐个执行</p></div><button className="icon-button" title="关闭" aria-label="关闭" onClick={onClose}><X size={18} /></button></header><label>采集模式<div className="segmented crawl-mode-tabs">{(['auto', 'public', 'authenticated'] as CrawlMode[]).map((mode) => <button type="button" key={mode} className={crawlMode === mode ? 'active' : ''} onClick={() => setCrawlMode(mode)}>{crawlModeLabel[mode]}</button>)}</div></label>{enabledSources.length ? <><div className="select-all"><span>选择信源</span><button onClick={() => setSelected(selected.length === enabledSources.length ? [] : enabledSources.map((source) => source.id))}>{selected.length === enabledSources.length ? '取消全选' : '全选'}</button></div><div className="source-check-list">{enabledSources.map((source) => <label key={source.id}><input type="checkbox" checked={selected.includes(source.id)} onChange={() => toggle(source.id)} /><span><strong>{source.name}</strong><small>{sourceTypeLabel[source.source_type]} · {source.target}</small></span></label>)}</div><label>每个信源最多采集<input type="number" min={1} max={100} value={maxNotes} onChange={(event) => setMaxNotes(Number(event.target.value))} /></label></> : <div className="empty-state compact"><strong>暂无可用信源</strong><span>请先添加并启用至少一个信源。</span><button className="secondary-button" onClick={onGoSources}>前往添加</button></div>}<footer><button className="secondary-button" onClick={onClose}>取消</button><button className="primary-button" disabled={loading || selected.length === 0 || maxNotes < 1} onClick={() => void onCreate(selected, maxNotes, crawlMode)}><Play size={17} />{loading ? '创建中...' : '开始采集'}</button></footer></div></div>;
}
