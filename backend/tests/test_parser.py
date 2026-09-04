from app.crawler.parser import build_crawled_note, extract_notes_from_payload, parse_compact_count, parse_note_id


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
    assert notes[0].completeness == "card"
    assert "xsec_token=token-value" in notes[0].note_url
    assert notes[0].media_items[0].media_url == "https://img.example/cover.jpg"


def test_detail_media_prefers_original_image_and_h264_video() -> None:
    note = build_crawled_note(
        {
            "note_id": "note-video",
            "type": "video",
            "desc": "视频正文",
            "image_list": [
                {
                    "width": 2160,
                    "height": 2880,
                    "url_pre": "https://sns-webpic-qc.xhscdn.com/preview.webp",
                    "url_default": "https://sns-webpic-qc.xhscdn.com/original.webp",
                }
            ],
            "video": {
                "image": {"url_default": "https://sns-webpic-qc.xhscdn.com/poster.webp"},
                "media": {
                    "stream": {
                        "h265": [{"master_url": "https://sns-video-qc.xhscdn.com/h265.mp4", "video_bitrate": 3000}],
                        "h264": [{"master_url": "https://sns-video-qc.xhscdn.com/h264.mp4", "video_bitrate": 1000}],
                    }
                },
            },
        }
    )

    assert note is not None
    assert note.media_items[0].media_url.endswith("original.webp")
    assert note.media_items[0].quality == "original"
    assert note.media_items[0].width == 2160
    assert note.media_items[1].media_type == "video"
    assert note.media_items[1].media_url.endswith("h264.mp4")


def test_payload_keeps_detail_media_when_same_note_also_has_preview_card() -> None:
    payload = {
        "detail": {
            "note_id": "same-note",
            "desc": "详情正文",
            "user": {"user_id": "u-1"},
            "image_list": [
                {
                    "width": 2160,
                    "height": 2880,
                    "url_default": "https://sns-webpic-qc.xhscdn.com/original.webp",
                }
            ],
        },
        "card": {
            "note_id": "same-note",
            "display_title": "列表卡片",
            "user": {"user_id": "u-1"},
            "cover": {
                "width": 540,
                "height": 720,
                "url_default": "https://sns-webpic-qc.xhscdn.com/preview.webp",
            },
        },
    }

    notes = extract_notes_from_payload(payload)

    assert len(notes) == 1
    assert notes[0].completeness == "complete"
    assert notes[0].media_items[0].quality == "original"
    assert notes[0].media_items[0].media_url.endswith("original.webp")
