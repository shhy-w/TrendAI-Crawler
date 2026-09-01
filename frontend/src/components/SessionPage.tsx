import { CheckCircle2, LogIn, RefreshCw, ShieldAlert } from 'lucide-react';
import type { CrawlerSession } from '../types/api';
import { formatDate, statusLabel } from '../lib/format';

export function SessionPage({ session, loading, onVerify, onLogin }: { session: CrawlerSession | null; loading: boolean; onVerify: () => Promise<void>; onLogin: () => Promise<void> }) {
  const active = session?.status === 'active';
  return (
    <section className="page-section">
      <div className="page-heading"><div><h1>登录会话</h1><p>采集任务依赖有效的小红书网页登录态</p></div></div>
      <div className="session-layout">
        <div className="session-main">
          <div className="session-state"><span className={`session-state-icon ${active ? 'active' : ''}`}>{active ? <CheckCircle2 size={22} /> : <ShieldAlert size={22} />}</span><div><span>主会话</span><strong>{session ? (statusLabel[session.status] ?? session.status) : '加载中'}</strong><p>{session?.last_verified_at ? `最近验证于 ${formatDate(session.last_verified_at)}` : '尚未执行在线验证'}</p></div></div>
          {session?.last_error ? <div className="inline-alert"><ShieldAlert size={18} /><span>{session.last_error}</span></div> : null}
          <div className="settings-list"><div><h2>运行保护</h2><p>单任务按信源串行执行；出现安全验证或登录失效后暂停对应信源并保留失败原因。</p></div><div><h2>会话存储</h2><p>登录资料仅保存在本机 Playwright profile，不写入数据库，也不会显示 Cookie 内容。</p></div><div><h2>数据边界</h2><p>只采集登录账号可正常浏览的公开笔记，不采集私信、粉丝关系或非公开个人信息。</p></div></div>
        </div>
        <aside className="login-panel"><span className="login-illustration"><LogIn size={32} /></span><h2>{active ? '会话可以使用' : '完成小红书登录'}</h2><p>{active ? '可以开始执行关键词、博主和单篇笔记采集。' : '点击后会打开本机浏览器，请使用小红书 App 扫码，登录成功后关闭窗口。'}</p><button className="primary-button block" disabled={loading || session?.status === 'login_running'} onClick={() => void onLogin()}><LogIn size={17} />{session?.status === 'login_running' ? '等待扫码...' : active ? '重新登录' : '打开登录窗口'}</button><button className="secondary-button block" disabled={loading || session?.status === 'login_running'} onClick={() => void onVerify()}><RefreshCw size={17} />验证当前会话</button></aside>
      </div>
    </section>
  );
}
