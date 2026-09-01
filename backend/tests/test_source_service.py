import pytest

from app.services.source_service import create_source


def test_create_keyword_source(db_session) -> None:
    source = create_source(db_session, "AI 工具", "keyword", " AI 工具 ")
    assert source.target == "AI 工具"
    assert source.enabled is True


def test_profile_source_requires_xiaohongshu_profile_url(db_session) -> None:
    with pytest.raises(ValueError, match="链接"):
        create_source(db_session, "错误链接", "profile", "https://example.com/user/profile/1")
