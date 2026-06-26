import { Network, RefreshCw } from 'lucide-react';
import type { ProxyItem } from '../types/api';

type ProxyPanelProps = {
  proxies: ProxyItem[];
  proxyName: string;
  proxyUrl: string;
  loading: boolean;
  onProxyNameChange: (value: string) => void;
  onProxyUrlChange: (value: string) => void;
  onAddProxy: () => void;
  onRefresh: () => void;
  onCheck: () => void;
};

export function ProxyPanel({
  proxies,
  proxyName,
  proxyUrl,
  loading,
  onProxyNameChange,
  onProxyUrlChange,
  onAddProxy,
  onRefresh,
  onCheck,
}: ProxyPanelProps) {
  return (
    <section className="panel proxy-panel">
      <div className="panel-title">
        <h2>代理池</h2>
        <button className="icon-button" onClick={onRefresh} title="刷新代理">
          <RefreshCw size={18} />
        </button>
      </div>
      <div className="form-grid">
        <label>
          名称
          <input value={proxyName} onChange={(event) => onProxyNameChange(event.target.value)} placeholder="proxy-1" />
        </label>
        <label>
          代理 URL
          <input value={proxyUrl} onChange={(event) => onProxyUrlChange(event.target.value)} placeholder="http://user:pass@host:port" />
        </label>
        <div className="button-row">
          <button className="primary-button" onClick={onAddProxy} disabled={loading}>
            <Network size={17} />
            添加
          </button>
          <button className="secondary-button" onClick={onCheck} disabled={loading || proxies.length === 0}>
            检查全部
          </button>
        </div>
      </div>
      <div className="proxy-list">
        {proxies.length === 0 ? (
          <p className="muted">暂无代理</p>
        ) : (
          proxies.map((proxy) => (
            <div className="proxy-item" key={proxy.id}>
              <span className={`status status-${proxy.status}`}>{proxy.status}</span>
              <strong>{proxy.name}</strong>
              <span>{proxy.success_count}/{proxy.failure_count}</span>
              {proxy.last_error ? <span className="error-text">{proxy.last_error}</span> : null}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
