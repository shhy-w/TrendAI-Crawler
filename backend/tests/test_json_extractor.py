from app.crawler.json_extractor import extract_posts_from_x_json


def test_extract_posts_from_nested_x_json() -> None:
    payload = {
        "data": {
            "search_by_raw_query": {
                "search_timeline": {
                    "timeline": {
                        "instructions": [
                            {
                                "entries": [
                                    {
                                        "content": {
                                            "itemContent": {
                                                "tweet_results": {
                                                    "result": {
                                                        "__typename": "Tweet",
                                                        "rest_id": "123",
                                                        "core": {
                                                            "user_results": {
                                                                "result": {
                                                                    "legacy": {
                                                                        "name": "OpenAI",
                                                                        "screen_name": "OpenAI",
                                                                    }
                                                                }
                                                            }
                                                        },
                                                        "views": {"count": "1000"},
                                                        "legacy": {
                                                            "created_at": "Fri Jun 26 09:00:00 +0000 2026",
                                                            "full_text": "AI agents are useful",
                                                            "reply_count": 1,
                                                            "retweet_count": 2,
                                                            "favorite_count": 3,
                                                            "extended_entities": {
                                                                "media": [
                                                                    {
                                                                        "type": "photo",
                                                                        "media_url_https": "https://pbs.twimg.com/media/a.jpg",
                                                                        "sizes": {"large": {"w": 1200, "h": 800}},
                                                                    }
                                                                ]
                                                            },
                                                        },
                                                    }
                                                }
                                            }
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }

    posts = extract_posts_from_x_json(payload, "AI")

    assert len(posts) == 1
    assert posts[0].x_post_id == "123"
    assert posts[0].author_handle == "OpenAI"
    assert posts[0].view_count == 1000
    assert posts[0].media_items[0].media_url == "https://pbs.twimg.com/media/a.jpg"
