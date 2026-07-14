from pathlib import Path


def test_frontend_uses_generic_paper_library_title():
    index_html = Path("static/index.html").read_text(encoding="utf-8")

    assert "ICML 2026 Paper Collections" not in index_html
    assert "Paper Collections" in index_html


def test_frontend_contains_conference_filter_behavior():
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert "conferenceList" in index_html
    assert "loadConferences" in app_js
    assert "setConferenceFilter" in app_js
    assert "/api/conferences" in app_js
    assert "conference" in app_js


def test_conference_filter_uses_separate_active_class():
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert 'button.className = "conference-filter"' in app_js
    assert "conference-filter active" not in app_js


def test_notes_ui_does_not_render_markdown_preview():
    app_js = Path("static/app.js").read_text(encoding="utf-8")
    styles_css = Path("static/styles.css").read_text(encoding="utf-8")

    assert "renderMarkdown" not in app_js
    assert "notes-preview" not in app_js
    assert "notes-preview" not in styles_css


def test_read_status_ui_uses_shared_toggle_and_api_endpoint():
    app_js = Path("static/app.js").read_text(encoding="utf-8")
    styles_css = Path("static/styles.css").read_text(encoding="utf-8")

    assert "makeReadStatusTag" in app_js
    assert "toggleReadStatus" in app_js
    assert "/read" in app_js
    assert "read-tag" in styles_css
