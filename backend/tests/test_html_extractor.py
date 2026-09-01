from app.crawler.html_extractor import extract_notes_from_html


def test_extract_public_note_cards_from_server_html() -> None:
    html = """
    <section class="note-item" data-note-id="note123">
      <a class="cover mask" href="/explore/note123?xsec_token=token-value">
        <img src="https://img.example/cover.webp">
        <span class="play-icon"></span>
      </a>
      <a class="title" href="/explore/note123"><span>AI 效率工作流</span></a>
      <div class="author-wrapper">
        <a class="author" href="/user/profile/user456">
          <img class="author-avatar" src="https://img.example/avatar.jpg">
          <span class="name">效率研究员</span>
        </a>
        <span class="count">1.2万</span>
      </div>
    </section>
    """

    notes = extract_notes_from_html(html)

    assert len(notes) == 1
    assert notes[0].platform_note_id == "note123"
    assert notes[0].note_type == "video"
    assert notes[0].title == "AI 效率工作流"
    assert notes[0].author_id == "user456"
    assert notes[0].author_name == "效率研究员"
    assert notes[0].like_count == 12000
    assert "xsec_token=token-value" in notes[0].note_url
    assert notes[0].media_items[0].media_url == "https://img.example/cover.webp"
