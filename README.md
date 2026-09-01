# RedScope

RedScope 是一个本地运行的小红书内容研究工具。它使用 Playwright 复用用户主动登录的小红书网页会话，按关键词、博主主页或单篇笔记链接采集公开笔记；FastAPI 提供接口，MySQL 存储笔记、媒体、信源、任务和互动指标快照，React 前端用于检索与管理。

## 主要能力

- 笔记库：按标题、正文、作者、信源和内容类型筛选，支持互动量、发布时间和采集时间排序。
- 信源管理：支持关键词、博主主页、单篇笔记链接三种入口。
- 采集任务：按信源独立记录进度、发现数、写入数与失败原因。
- 登录会话：从页面打开本地浏览器完成扫码登录，并在线验证会话状态。
- 趋势基础：每次更新笔记时保存点赞、收藏、评论和分享指标快照。

## 本地启动

1. 准备环境变量：

```bash
cp .env.example .env
```

2. 启动 MySQL：

```bash
docker compose up -d mysql
```

3. 安装并启动后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
alembic upgrade head
uvicorn app.main:app --reload
```

4. 安装并启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。首次使用先进入“登录会话”，点击“打开登录窗口”，使用小红书 App 扫码登录并关闭浏览器窗口，然后点击“验证当前会话”。也可以从命令行登录：

```bash
cd backend
source .venv/bin/activate
python scripts/open_xhs_login.py
```

## 从旧版本升级

`202611010005_xiaohongshu_rebuild` 会删除原 X 平台的帖子、token、queryId、代理和任务数据，并创建小红书数据结构。执行迁移前，如需保留旧数据，请先自行备份数据库。

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

## 采集策略

采集器不会直接调用未公开的签名接口，而是在正常浏览器会话中监听页面已经产生的 JSON 响应，并以可见 DOM 作为降级路径。任务默认串行执行，出现登录失效、安全验证、限频或页面结构变化时会停止对应信源并保存失败信息；空内容或安全验证会把 HTML、截图和元信息写入 `CRAWLER_DEBUG_DIR`。

小红书网页结构和访问策略可能变化。该项目适合作为低频、内部内容研究工具，不应绕过验证码、访问控制或平台限制，也不适合作为承诺稳定 SLA 的公共数据服务。仅采集账号有权正常浏览的公开内容，并遵守适用的平台条款、版权和个人信息保护要求。

## 项目结构

- `backend/app/crawler/`：小红书页面采集与结构化解析。
- `backend/app/models/`：笔记、媒体、信源、任务、会话和指标模型。
- `backend/app/api/`：笔记、信源、任务和会话接口。
- `frontend/src/`：React 内容研究工作台。
- `docker-compose.yml`：本地 MySQL。
