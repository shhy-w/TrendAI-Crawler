export function compactNumber(value: number): string {
  if (value >= 100_000_000) return `${trim(value / 100_000_000)}亿`;
  if (value >= 10_000) return `${trim(value / 10_000)}万`;
  return new Intl.NumberFormat('zh-CN').format(value);
}

function trim(value: number): string {
  return value >= 10 ? Math.round(value).toString() : value.toFixed(1).replace('.0', '');
}

export function formatDate(value: string | null, fallback = '尚未运行'): string {
  if (!value) return fallback;
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export const sourceTypeLabel: Record<string, string> = {
  explore: '发现页',
  keyword: '关键词',
  profile: '博主主页',
  note: '笔记链接',
};

export const statusLabel: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  succeeded: '已完成',
  partial: '部分完成',
  failed: '失败',
  active: '正常',
  auth_required: '需要登录',
  verifying: '验证中',
  login_running: '等待扫码',
  error: '异常',
  unknown: '未验证',
};

export const crawlModeLabel: Record<string, string> = {
  auto: '自动模式',
  public: '匿名模式',
  authenticated: '登录模式',
};

export const completenessLabel: Record<string, string> = {
  card: '卡片数据',
  partial: '部分详情',
  complete: '完整详情',
};
