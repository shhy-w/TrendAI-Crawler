# TrendAI Crawler

本项目是一个本地 MVP：使用 Playwright 采集 X 上的 AI、vibe coding、agent 等热门内容，FastAPI 提供接口，MySQL 存储数据，React 前端用于查看文章和媒体外链。采集器默认只跑公开通道且 headless 运行，不会弹登录窗口；需要时可手动启用登录态 fallback。

## 目录

- `backend/`：FastAPI、SQLAlchemy、Alembic、Playwright 爬虫。
- `frontend/`：Vite + React + TypeScript 前端。
- `docker-compose.yml`：本地 MySQL。

## 本地启动

1. 准备环境变量：

```bash
cp .env.example .env
```

2. 启动 MySQL：

```bash
docker compose up -d mysql
```

3. 启动后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
alembic upgrade head
uvicorn app.main:app --reload
```

4. 可选：登录 X：

```bash
cd backend
source .venv/bin/activate
python scripts/open_x_login.py
```

脚本会打开持久化浏览器窗口。手动登录 X 后关闭窗口，后续采集会复用 `CRAWLER_PROFILE_DIR` 中的登录态。默认配置 `CRAWLER_CHANNEL=public` 且 `CRAWLER_HEADLESS=true`，不会打开登录窗口；如果你确实要公开失败后 fallback 到登录态，设置 `CRAWLER_CHANNEL=dual` 和 `CRAWLER_FALLBACK_TO_AUTH=true`。

5. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

默认访问 `http://localhost:5173`。

## 采集说明

第一版只支持手动触发。前端会调用 `POST /api/crawl-jobs`，后端创建任务并异步执行 Playwright 采集。媒体不下载，只保存图片、视频缩略图等外链。

X 页面结构、公开访问策略和风控会变化。如果任务失败，请先查看 `crawl_jobs.error_message` 或后端日志。
