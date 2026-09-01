import { CheckCircle2, LogIn, RefreshCw, ShieldAlert } from 'lucide-react';
import type { CrawlerSession } from '../types/api';
import { formatDate } from '../lib/format';

export function SessionPage({ session, loading, onVerify, onLogin }: { session: CrawlerSession | null; loading: boolean; onVerify: () => Promise<void>; onLogin: () => Promise<void> }) {
  const active = session?.status === 'active';
  return (
    <section className="page-section">
      <div className="page-heading"><div><h1>登录会话</h1><p>匿名采集无需登录，登录会话用于扩展受限内容能力</p></div></div>
      <div className="session-layout">
        <div className="session-main">
          <div className="session-state"><span className={`session-state-icon ${active ? 'active' : 'public'}`}>{active ? <CheckCircle2 size={22} /> : <ShieldAlert size={22} />}</span><div><span>当前采集能力</span><strong>{active ? '登录与匿名模式可用' : '匿名模式可用'}</strong><p>{session?.last_verified_at ? `登录会话最近验证于 ${formatDate(session.last_verified_at)}` : '登录状态不影响匿名公开内容采集'}</p></div></div>
          {session?.last_error ? <div className="inline-alert"><ShieldAlert size={18} /><span>{session.last_error}</span></div> : null}
          <div className="settings-list"><div><h2>运行保护</h2><p>匿名通道使用临时浏览器，登录通道使用本地会话；出现安全验证后暂停对应信源并保留失败原因。</p></div><div><h2>会话存储</h2><p>登录资料仅保存在本机 Playwright profile，不写入数据库，也不会显示 Cookie 内容。</p></div><div><h2>数据边界</h2><p>匿名模式采集公开卡片，登录模式用于受限搜索和详情补全，不采集私信或非公开个人信息。</p></div></div>
        </div>
        <aside className="login-panel"><span className="login-illustration"><LogIn size={32} /></span><h2>{active ? '登录通道可用' : '启用完整采集'}</h2><p>{active ? '自动模式会在匿名结果不足时使用登录会话。' : '扫码登录可扩展关键词搜索、博主列表和笔记详情能力。'}</p><button className="primary-button block" disabled={loading || session?.status === 'login_running'} onClick={() => void onLogin()}><LogIn size={17} />{session?.status === 'login_running' ? '等待扫码...' : active ? '重新登录' : '打开登录窗口'}</button><button className="secondary-button block" disabled={loading || session?.status === 'login_running'} onClick={() => void onVerify()}><RefreshCw size={17} />验证登录会话</button></aside>
      </div>
    </section>
  );
}
