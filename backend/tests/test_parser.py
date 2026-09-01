from app.crawler.parser import extract_notes_from_payload, parse_compact_count, parse_note_id


def test_parse_note_id() -> None:
    assert parse_note_id("https://www.xiaohongshu.com/explore/64a123bc000000001201abcd?xsec_token=test") == "64a123bc000000001201abcd"


def test_parse_compact_count() -> None:
    assert parse_compact_count("1.2万") == 12000
    assert parse_compact_count("3K") == 3000
    assert parse_compact_count(42) == 42


def test_extract_notes_from_search_payload() -> None:
    payload = {
        "data": {
            "items": [
                {
                    "id": "64a123bc000000001201abcd",
                    "xsec_token": "token-value",
                    "note_card": {
                        "type": "normal",
                        "display_title": "AI 效率工具清单",
                        "user": {"user_id": "u-1", "nickname": "效率研究员", "avatar": "https://img.example/avatar.jpg"},
                        "interact_info": {
                            "liked_count": "1.2万",
                            "collected_count": "3200",
                            "comment_count": "88",
                            "shared_count": "42",
                        },
                        "cover": {"url_default": "https://img.example/cover.jpg", "width": 1080, "height": 1440},
                    },
                }
            ]
        }
    }

    notes = extract_notes_from_payload(payload)

    assert len(notes) == 1
    assert notes[0].platform_note_id == "64a123bc000000001201abcd"
    assert notes[0].title == "AI 效率工具清单"
    assert notes[0].author_name == "效率研究员"
    assert notes[0].like_count == 12000
    assert notes[0].collect_count == 3200
    assert "xsec_token=token-value" in notes[0].note_url
    assert notes[0].media_items[0].media_url == "https://img.example/cover.jpg"
