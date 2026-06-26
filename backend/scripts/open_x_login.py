import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.crawler.x_crawler import open_login_browser


if __name__ == "__main__":
    asyncio.run(open_login_browser())
