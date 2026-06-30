from pathlib import Path


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
