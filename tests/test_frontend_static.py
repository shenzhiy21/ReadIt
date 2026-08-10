from pathlib import Path


def test_frontend_uses_generic_paper_library_title():
    index_html = Path("static/index.html").read_text(encoding="utf-8")

    assert "ICML 2026 Paper Collections" not in index_html
    assert "Paper Collections" in index_html


def test_frontend_contains_publication_filter_behavior():
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert "publicationList" in index_html
    assert "loadPublications" in app_js
    assert "setPublicationFilter" in app_js
    assert "/api/publications" in app_js
    assert "publication" in app_js
    assert "conference" not in index_html.casefold()
    assert "conference" not in app_js.casefold()


def test_publication_filter_uses_separate_active_class():
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert 'button.className = "publication-filter"' in app_js
    assert "publication-filter active" not in app_js


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


def test_frontend_pages_paper_list_in_batches_of_ten():
    index_html = Path("static/index.html").read_text(encoding="utf-8")
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert 'id="paginationControls"' in index_html
    assert "const PAGE_SIZE = 10;" in app_js
    assert 'params.set("limit", String(PAGE_SIZE));' in app_js
    assert 'params.set("offset", String(state.page * PAGE_SIZE));' in app_js
    assert 'params.set("limit", "10000");' not in app_js


def test_paper_source_link_uses_generic_label():
    app_js = Path("static/app.js").read_text(encoding="utf-8")

    assert 'makeExternalLink(paper.url, "Paper page")' in app_js
    assert 'makeExternalLink(paper.url, "OpenReview")' not in app_js


def test_collection_view_offers_quick_remove_on_each_paper():
    app_js = Path("static/app.js").read_text(encoding="utf-8")
    styles_css = Path("static/styles.css").read_text(encoding="utf-8")

    assert 'state.activeFilter === "collection" && state.activeCollectionId' in app_js
    assert 'removeButton.textContent = "Remove from collection"' in app_js
    assert "event.stopPropagation();" in app_js
    assert "await setMembership(paper.id, state.activeCollectionId, false);" in app_js
    assert ".quick-remove-button" in styles_css
