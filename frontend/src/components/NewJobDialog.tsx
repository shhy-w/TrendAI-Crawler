import { LockKeyhole, Play, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { CrawlMode, Source } from '../types/api';
import { crawlModeLabel, sourceTypeLabel } from '../lib/format';

type Props = {
  open: boolean;
  sources: Source[];
  sessionActive: boolean;
  loading: boolean;
  onClose: () => void;
  onCreate: (sourceIds: number[], maxNotes: number, crawlMode: CrawlMode) => Promise<void>;
  onGoSources: () => void;
};

export function NewJobDialog({ open, sources, sessionActive, loading, onClose, onCreate, onGoSources }: Props) {
  const enabledSources = useMemo(() => sources.filter((source) => source.enabled), [sources]);
  const [selected, setSelected] = useState<number[]>([]);
  const [maxNotes, setMaxNotes] = useState(20);
  const [crawlMode, setCrawlMode] = useState<CrawlMode>('auto');

  const eligibleSources = useMemo(
    () => enabledSources.filter((source) => isEligible(source, crawlMode, sessionActive)),
    [enabledSources, crawlMode, sessionActive],
  );

  useEffect(() => {
    if (open) setSelected(eligibleSources.map((source) => source.id));
  }, [open, eligibleSources]);

  if (!open) return null;

  function toggle(id: number) {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  function selectAll() {
    setSelected(selected.length === eligibleSources.length ? [] : eligibleSources.map((source) => source.id));
  }

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="dialog job-dialog" onMouseDown={(event) => event.stopPropagation()}>
        <header>
          <div><h2>新建采集</h2><p>本次任务会按所选信源逐个执行</p></div>
          <button className="icon-button" title="关闭" aria-label="关闭" onClick={onClose}><X size={18} /></button>
        </header>
        <label>
          采集模式
          <div className="segmented crawl-mode-tabs">
            {(['auto', 'public', 'authenticated'] as CrawlMode[]).map((mode) => (
              <button type="button" key={mode} className={crawlMode === mode ? 'active' : ''} onClick={() => setCrawlMode(mode)}>
                {crawlModeLabel[mode]}
              </button>
            ))}
          </div>
        </label>

        {!sessionActive && crawlMode === 'authenticated' ? (
          <div className="inline-alert"><LockKeyhole size={17} /><span>登录会话不可用，请先完成扫码登录。</span></div>
        ) : null}

        {enabledSources.length ? (
          <>
            <div className="select-all">
              <span>选择信源</span>
              <button disabled={eligibleSources.length === 0} onClick={selectAll}>
                {selected.length === eligibleSources.length && eligibleSources.length ? '取消全选' : '全选可用信源'}
              </button>
            </div>
            <div className="source-check-list">
              {enabledSources.map((source) => {
                const eligible = isEligible(source, crawlMode, sessionActive);
                return (
                  <label className={eligible ? '' : 'disabled'} key={source.id}>
                    <input type="checkbox" disabled={!eligible} checked={selected.includes(source.id)} onChange={() => toggle(source.id)} />
                    <span>
                      <strong>{source.name}</strong>
                      <small>
                        {sourceTypeLabel[source.source_type]} · {source.target}
                        {!eligible ? ' · 需要登录' : source.public_supported ? ' · 匿名可用' : ''}
                      </small>
                    </span>
                  </label>
                );
              })}
            </div>
            <label>
              每个信源最多采集
              <input type="number" min={1} max={100} value={maxNotes} onChange={(event) => setMaxNotes(Number(event.target.value))} />
            </label>
          </>
        ) : (
          <div className="empty-state compact">
            <strong>暂无可用信源</strong><span>请先添加并启用至少一个信源。</span>
            <button className="secondary-button" onClick={onGoSources}>前往添加</button>
          </div>
        )}
        <footer>
          <button className="secondary-button" onClick={onClose}>取消</button>
          <button className="primary-button" disabled={loading || selected.length === 0 || maxNotes < 1} onClick={() => void onCreate(selected, maxNotes, crawlMode)}>
            <Play size={17} />{loading ? '创建中...' : '开始采集'}
          </button>
        </footer>
      </div>
    </div>
  );
}

function isEligible(source: Source, mode: CrawlMode, sessionActive: boolean): boolean {
  if (mode === 'public') return source.public_supported;
  if (mode === 'authenticated') return sessionActive;
  return source.public_supported || sessionActive;
}
