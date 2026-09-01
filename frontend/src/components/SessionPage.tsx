import { CheckCircle2, LogIn, RefreshCw, Save, ShieldAlert, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { AccountProtectionSettings, CrawlerSession } from '../types/api';
import { formatDate } from '../lib/format';

type Props = {
  session: CrawlerSession | null;
  loading: boolean;
  onVerify: () => Promise<void>;
  onLogin: () => Promise<void>;
  onUpdateProtection: (settings: AccountProtectionSettings) => Promise<void>;
};

const defaultProtection: AccountProtectionSettings = {
  protection_enabled: true,
  daily_request_limit: 60,
  cooldown_seconds: 30,
  failure_threshold: 2,
  lockout_minutes: 360,
};

export function SessionPage({ session, loading, onVerify, onLogin, onUpdateProtection }: Props) {
  const [protection, setProtection] = useState<AccountProtectionSettings>(defaultProtection);
  const loginActive = session?.status === 'active';
  const protectionBlocked = session?.status === 'protection_blocked';
  const budgetPercent = session ? Math.min(100, Math.round(session.daily_request_count / session.daily_request_limit * 100)) : 0;

  useEffect(() => {
    if (!session) return;
    setProtection({
      protection_enabled: session.protection_enabled,
      daily_request_limit: session.daily_request_limit,
      cooldown_seconds: session.cooldown_seconds,
      failure_threshold: session.failure_threshold,
      lockout_minutes: session.lockout_minutes,
    });
  }, [session]);

  async function saveProtection() {
    try {
      await onUpdateProtection(protection);
    } catch {
      // App displays the API error and keeps the current form values.
    }
  }

  return (
    <section className="page-section">
      <div className="page-heading"><div><h1>登录会话</h1><p>匿名采集无需登录，登录会话用于扩展受限内容能力</p></div></div>
      <div className="session-layout">
        <div className="session-main">
          <div className="session-state">
            <span className={`session-state-icon ${loginActive ? 'active' : protectionBlocked ? '' : 'public'}`}>
              {loginActive ? <CheckCircle2 size={22} /> : <ShieldAlert size={22} />}
            </span>
            <div>
              <span>当前采集能力</span>
              <strong>{protectionBlocked ? '登录采集已被账号保护暂停' : loginActive ? '登录与匿名模式可用' : '匿名模式可用'}</strong>
              <p>{protectionBlocked && session?.blocked_until ? `恢复时间 ${formatDate(session.blocked_until)}` : session?.last_verified_at ? `登录会话最近验证于 ${formatDate(session.last_verified_at)}` : '登录状态不影响匿名公开内容采集'}</p>
            </div>
          </div>
          {session?.last_error ? <div className="inline-alert"><ShieldAlert size={18} /><span>{session.last_error}</span></div> : null}

          <section className="protection-section">
            <div className="protection-heading">
              <div><ShieldCheck size={20} /><div><h2>账号保护模式</h2><p>仅约束登录通道，匿名采集不计入预算</p></div></div>
              <label className="switch">
                <input type="checkbox" checked={protection.protection_enabled} onChange={(event) => setProtection({ ...protection, protection_enabled: event.target.checked })} />
                <span /><b>{protection.protection_enabled ? '已开启' : '已关闭'}</b>
              </label>
            </div>

            <div className="protection-usage">
              <div><span>今日页面预算</span><strong>{session?.daily_request_count ?? 0} / {session?.daily_request_limit ?? protection.daily_request_limit}</strong></div>
              <div><span>连续风险异常</span><strong>{session?.consecutive_failures ?? 0} / {session?.failure_threshold ?? protection.failure_threshold}</strong></div>
              <div><span>暂停至</span><strong>{session?.blocked_until ? formatDate(session.blocked_until) : '未暂停'}</strong></div>
            </div>
            <div className="budget-progress" role="progressbar" aria-label="今日登录访问预算" aria-valuemin={0} aria-valuemax={session?.daily_request_limit ?? protection.daily_request_limit} aria-valuenow={session?.daily_request_count ?? 0}><i style={{ width: `${budgetPercent}%` }} /></div>

            <div className="protection-fields">
              <label>每日页面动作上限<input type="number" min={10} max={500} disabled={!protection.protection_enabled} value={protection.daily_request_limit} onChange={(event) => setProtection({ ...protection, daily_request_limit: Number(event.target.value) })} /></label>
              <label>任务冷却（秒）<input type="number" min={5} max={600} disabled={!protection.protection_enabled} value={protection.cooldown_seconds} onChange={(event) => setProtection({ ...protection, cooldown_seconds: Number(event.target.value) })} /></label>
              <label>连续异常阈值<input type="number" min={1} max={10} disabled={!protection.protection_enabled} value={protection.failure_threshold} onChange={(event) => setProtection({ ...protection, failure_threshold: Number(event.target.value) })} /></label>
              <label>暂停时长（分钟）<input type="number" min={15} max={1440} disabled={!protection.protection_enabled} value={protection.lockout_minutes} onChange={(event) => setProtection({ ...protection, lockout_minutes: Number(event.target.value) })} /></label>
            </div>
            <div className="protection-actions"><button className="secondary-button" disabled={loading || !session} onClick={() => void saveProtection()}><Save size={16} />保存保护设置</button></div>
          </section>

          <div className="settings-list">
            <div><h2>运行保护</h2><p>登录任务串行执行；验证码、限频或风险网络会累计异常并触发暂停。</p></div>
            <div><h2>会话存储</h2><p>登录资料仅保存在本机 Playwright profile，不写入数据库，也不会显示 Cookie 内容。</p></div>
            <div><h2>数据边界</h2><p>匿名模式采集公开卡片，登录模式用于受限搜索和详情补全，不采集私信或非公开个人信息。</p></div>
          </div>
        </div>
        <aside className="login-panel">
          <span className="login-illustration"><LogIn size={32} /></span>
          <h2>{loginActive || protectionBlocked ? '登录通道已连接' : '启用完整采集'}</h2>
          <p>{protectionBlocked ? '账号保护暂停期间仍可继续匿名采集。' : loginActive ? '自动模式只在信源需要时使用登录会话。' : '扫码登录可扩展关键词搜索、博主列表和笔记详情能力。'}</p>
          <button className="primary-button block" disabled={loading || session?.status === 'login_running' || protectionBlocked} onClick={() => void onLogin()}><LogIn size={17} />{session?.status === 'login_running' ? '等待扫码...' : loginActive ? '重新登录' : '打开登录窗口'}</button>
          <button className="secondary-button block" disabled={loading || session?.status === 'login_running'} onClick={() => void onVerify()}><RefreshCw size={17} />验证登录会话</button>
        </aside>
      </div>
    </section>
  );
}
