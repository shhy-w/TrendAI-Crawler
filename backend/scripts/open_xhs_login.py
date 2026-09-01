from __future__ import annotations

import asyncio

from app.crawler.xhs_crawler import open_xhs_login


if __name__ == "__main__":
    print("请在打开的浏览器中完成小红书扫码登录，登录成功后关闭浏览器窗口。")
    asyncio.run(open_xhs_login())
