import { Plus, Rss, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import type { Source, SourceType } from '../types/api';
import { formatDate, sourceTypeLabel } from '../lib/format';

type Props = {
  sources: Source[];
  onCreate: (name: string, type: SourceType, target: string) => Promise<void>;
  onToggle: (source: Source) => Promise<void>;
  onDelete: (source: Source) => Promise<void>;
};

export function SourcesPage({ sources, onCreate, onToggle, onDelete }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [sourceType, setSourceType] = useState<SourceType>('keyword');
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [saving, setSaving] = useState(false);
  const exploreChannels = [
    { value: 'homefeed_recommend', label: '推荐' },
    { value: 'fashion_v3', label: '穿搭' },
    { value: 'food_v3', label: '美食' },
    { value: 'travel_v3', label: '旅行' },
    { value: 'career_v3', label: '职场' },
  ];

  async function submit() {
    setSaving(true);
    try {
      await onCreate(name, sourceType, target);
      setName(''); setTarget(''); setShowForm(false);
    } catch {
      // App displays the API error; keep the dialog open so the input can be corrected.
    } finally { setSaving(false); }
  }

  return (
    <section className="page-section">
      <div className="page-heading"><div><h1>信源管理</h1><p>统一维护关键词、博主主页和单篇笔记</p></div><button className="primary-button" onClick={() => setShowForm(true)}><Plus size={17} />添加信源</button></div>
      {sources.length === 0 ? <div className="empty-state"><Rss size={28} /><strong>还没有信源</strong><span>先添加一个关键词、博主主页或笔记链接。</span><button className="primary-button" onClick={() => setShowForm(true)}><Plus size={17} />添加信源</button></div> : (
        <div className="table-wrap source-table"><table><thead><tr><th>信源</th><th>类型</th><th>匿名能力</th><th>采集目标</th><th>最近结果</th><th>最后运行</th><th>状态</th><th><span className="sr-only">操作</span></th></tr></thead><tbody>{sources.map((source) => <tr key={source.id}><td><strong>{source.name}</strong>{source.last_error ? <span className="row-error">{source.last_error}</span> : null}</td><td>{sourceTypeLabel[source.source_type]}</td><td><span className={`status ${source.public_supported ? 'status-succeeded' : 'status-needs_auth'}`}>{source.public_supported ? '可用' : '需登录'}</span></td><td className="target-cell">{source.target}</td><td>{source.last_result_count} 条</td><td>{formatDate(source.last_run_at)}</td><td><label className="switch"><input type="checkbox" checked={source.enabled} onChange={() => void onToggle(source)} /><span /><b>{source.enabled ? '启用' : '停用'}</b></label></td><td><button className="icon-button danger" title="删除信源" aria-label={`删除 ${source.name}`} onClick={() => void onDelete(source)}><Trash2 size={17} /></button></td></tr>)}</tbody></table></div>
      )}
      {showForm ? <div className="modal-backdrop" onMouseDown={() => setShowForm(false)}><div className="dialog" onMouseDown={(event) => event.stopPropagation()}><header><div><h2>添加信源</h2><p>选择一种采集入口</p></div><button className="icon-button" title="关闭" aria-label="关闭" onClick={() => setShowForm(false)}><X size={18} /></button></header><div className="segmented source-type-tabs">{(['explore', 'keyword', 'profile', 'note'] as SourceType[]).map((type) => <button key={type} className={sourceType === type ? 'active' : ''} onClick={() => { setSourceType(type); setTarget(type === 'explore' ? 'homefeed_recommend' : ''); }}>{sourceTypeLabel[type]}</button>)}</div><label>信源名称<input value={name} onChange={(event) => setName(event.target.value)} placeholder={sourceType === 'explore' ? '例如：发现页推荐' : sourceType === 'keyword' ? '例如：AI 效率工具' : '便于识别的名称'} /></label>{sourceType === 'explore' ? <label>发现频道<select value={target || 'homefeed_recommend'} onChange={(event) => setTarget(event.target.value)}>{exploreChannels.map((channel) => <option key={channel.value} value={channel.value}>{channel.label}</option>)}</select></label> : <label>{sourceType === 'keyword' ? '搜索关键词' : sourceType === 'profile' ? '博主主页链接' : '笔记链接'}<input value={target} onChange={(event) => setTarget(event.target.value)} placeholder={sourceType === 'keyword' ? 'AI 效率工具' : 'https://www.xiaohongshu.com/...'} /></label>}<footer><button className="secondary-button" onClick={() => setShowForm(false)}>取消</button><button className="primary-button" disabled={saving || !name.trim() || !(target || sourceType === 'explore')} onClick={() => void submit()}>{saving ? '保存中...' : '保存信源'}</button></footer></div></div> : null}
    </section>
  );
}
