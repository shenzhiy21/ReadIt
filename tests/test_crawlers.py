import pytest

from paperlib.crawlers.dblp import (
    DblpCompletenessError,
    build_summary as build_dblp_summary,
    count_html_articles,
    normalize_dblp_author_name,
    parse_dblp_xml,
    validate_completeness,
    write_outputs as write_dblp_outputs,
)
from paperlib.crawlers.publications import get_publication
from paperlib.crawlers.openreview import (
    build_summary,
    normalize_fallback_row,
    normalize_note,
    output_paths,
)


def test_get_publication_returns_icml2026_config():
    config = get_publication("icml2026")

    assert config.key == "icml2026"
    assert config.invitation == "ICML.cc/2026/Conference/-/Submission"
    assert "ICML 2026 regular" in config.venues
    assert config.venueid == "ICML.cc/2026/Conference"


def test_get_publication_returns_iclr2026_config():
    config = get_publication("iclr2026")

    assert config.key == "iclr2026"
    assert config.name == "ICLR 2026"
    assert config.invitation == "ICLR.cc/2026/Conference/-/Submission"
    assert "ICLR 2026 Poster" in config.venues
    assert config.venueid == "ICLR.cc/2026/Conference"


def test_get_publication_returns_tvcg2025_dblp_config():
    config = get_publication("tvcg2025")

    assert config.name == "TVCG 2025"
    assert config.year == 2025
    assert config.volume == 31
    assert config.expected_issues == tuple(str(issue) for issue in range(1, 13))
    assert config.html_url == "https://dblp.org/db/journals/tvcg/tvcg31.html"
    assert config.xml_url == "https://dblp.org/db/journals/tvcg/tvcg31.xml"


def test_tvcg_publications_cover_2023_through_2026():
    expected = {
        "tvcg2023": (2023, 29),
        "tvcg2024": (2024, 30),
        "tvcg2025": (2025, 31),
        "tvcg2026": (2026, 32),
    }

    for key, (year, volume) in expected.items():
        config = get_publication(key)
        assert config.year == year
        assert config.volume == volume

    assert get_publication("tvcg2026").expected_issues == ()


def test_iclr2026_fallback_includes_all_main_accepted_statuses():
    config = get_publication("iclr2026")

    assert ("Poster", "ICLR 2026 Poster") in config.fallback_status_venues
    assert ("SPOT", "ICLR 2026 Spotlight") in config.fallback_status_venues
    assert ("Oral", "ICLR 2026 Oral") in config.fallback_status_venues


def test_conference_configs_have_display_names():
    assert get_publication("icml2026").name == "ICML 2026"


def test_get_publication_rejects_unknown_key():
    with pytest.raises(KeyError, match="Unknown publication"):
        get_publication("missing")


def test_normalize_note_extracts_openreview_fields():
    note = {
        "id": "abc",
        "forum": "abc",
        "number": 42,
        "content": {
            "venue": {"value": "ICML 2026 regular"},
            "title": {"value": "Chart QA"},
            "authors": {"value": ["A", "B"]},
            "authorids": {"value": ["~A1", "~B1"]},
            "abstract": {"value": "Abstract"},
            "primary_area": {"value": "evaluation"},
            "keywords": {"value": ["chart"]},
            "TLDR": {"value": "Short"},
            "pdf": {"value": "/pdf/abc.pdf"},
        },
    }

    paper = normalize_note(note)

    assert paper["openreview_id"] == "abc"
    assert paper["title"] == "Chart QA"
    assert paper["authors"] == ["A", "B"]
    assert paper["url"] == "https://openreview.net/forum?id=abc"


def test_normalize_fallback_row_maps_accepted_jsonl_fields():
    row = {
        "id": "abc",
        "status": "Poster",
        "title": "Chart QA",
        "author": "A;B",
        "authorids": "~A1;~B1",
        "abstract": "Abstract",
        "primary_area": "evaluation",
        "keywords": "chart;qa",
        "tldr": "Short",
        "site": "https://openreview.net/forum?id=abc",
    }

    paper = normalize_fallback_row(row, "ICLR 2026 Poster")

    assert paper["openreview_id"] == "abc"
    assert paper["forum"] == "abc"
    assert paper["venue"] == "ICLR 2026 Poster"
    assert paper["title"] == "Chart QA"
    assert paper["authors"] == ["A", "B"]
    assert paper["authorids"] == ["~A1", "~B1"]
    assert paper["keywords"] == ["chart", "qa"]
    assert paper["url"] == "https://openreview.net/forum?id=abc"


def test_output_paths_use_standard_names(tmp_path):
    paths = output_paths(tmp_path, "icml2026")

    assert paths.jsonl == tmp_path / "raw" / "icml2026" / "accepted_papers.jsonl"
    assert paths.csv == tmp_path / "raw" / "icml2026" / "accepted_papers.csv"
    assert paths.summary == tmp_path / "raw" / "icml2026" / "summary.json"


def test_build_summary_uses_actual_output_paths(tmp_path):
    config = get_publication("icml2026")
    paths = output_paths(tmp_path, "icml2026")

    summary = build_summary(config, [], {}, paths)

    assert summary["outputs"]["jsonl"] == str(paths.jsonl)
    assert summary["outputs"]["csv"] == str(paths.csv)


DBLP_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<dblp>
  <article key="journals/tvcg/Alpha25">
    <author pid="11/a">Ada Example</author>
    <author pid="22/b">Bo Example</author>
    <title>Visual <i>Analytics</i>.</title>
    <pages>1-10</pages>
    <year>2025</year>
    <volume>31</volume>
    <journal>IEEE Trans. Vis. Comput. Graph.</journal>
    <number>1</number>
    <ee>https://doi.org/10.1109/TVCG.2025.1</ee>
  </article>
  <article key="journals/tvcg/Beta25">
    <author pid="33/c">Chen Example</author>
    <title>Second Paper.</title>
    <pages>11-20</pages>
    <year>2025</year>
    <volume>31</volume>
    <journal>IEEE Trans. Vis. Comput. Graph.</journal>
    <number>2</number>
    <ee>https://example.test/paper</ee>
  </article>
</dblp>
"""


def test_parse_dblp_xml_extracts_volume_metadata():
    papers = parse_dblp_xml(DBLP_XML, expected_year=2025, expected_volume=31)

    assert len(papers) == 2
    assert papers[0]["id"] == "journals/tvcg/Alpha25"
    assert papers[0]["title"] == "Visual Analytics"
    assert papers[0]["authors"] == ["Ada Example", "Bo Example"]
    assert papers[0]["doi"] == "10.1109/tvcg.2025.1"
    assert papers[0]["url"] == "https://dblp.org/rec/journals/tvcg/Alpha25"
    assert papers[1]["doi"] == ""


def test_normalize_dblp_author_name_removes_homonym_suffix_only():
    assert normalize_dblp_author_name("Yu Zhang 0043") == "Yu Zhang"
    assert normalize_dblp_author_name("Wei Zeng 0004") == "Wei Zeng"
    assert normalize_dblp_author_name("Agent 47") == "Agent 47"


def test_parse_dblp_xml_cleans_author_name_and_preserves_pid():
    xml = DBLP_XML.replace(b">Ada Example</author>", b">Ada Example 0043</author>")

    papers = parse_dblp_xml(xml, expected_year=2025, expected_volume=31)

    assert papers[0]["authors"][0] == "Ada Example"
    assert papers[0]["author_pids"][0] == "11/a"


def test_parse_dblp_xml_accepts_current_bht_volume_wrapper():
    wrapped = DBLP_XML.replace(
        b"<dblp>", b'<bht key="db/journals/tvcg/tvcg31.bht"><dblpcites><r>'
    ).replace(b"</dblp>", b"</r></dblpcites></bht>")

    papers = parse_dblp_xml(wrapped, expected_year=2025, expected_volume=31)

    assert len(papers) == 2


def test_parse_dblp_xml_rejects_out_of_scope_records():
    xml = DBLP_XML.replace(b"<year>2025</year>", b"<year>2024</year>", 1)

    with pytest.raises(DblpCompletenessError, match="out-of-scope"):
        parse_dblp_xml(xml, expected_year=2025, expected_volume=31)


def test_count_html_articles_counts_only_article_entries():
    html = """
    <ul>
      <li class="entry article">one</li>
      <li class="article entry toc">two</li>
      <li class="entry inproceedings">not an article</li>
    </ul>
    """

    assert count_html_articles(html) == 2


def test_validate_completeness_rejects_xml_html_count_mismatch():
    papers = parse_dblp_xml(DBLP_XML, expected_year=2025, expected_volume=31)

    with pytest.raises(DblpCompletenessError, match="XML has 2.*HTML has 1"):
        validate_completeness(papers, html_article_count=1)


def test_validate_completeness_rejects_missing_expected_issue():
    papers = parse_dblp_xml(DBLP_XML, expected_year=2025, expected_volume=31)

    with pytest.raises(DblpCompletenessError, match="missing expected issues: 3"):
        validate_completeness(papers, html_article_count=2, expected_issues=("1", "2", "3"))


def test_validate_completeness_requires_contiguous_current_year_issues():
    papers = parse_dblp_xml(DBLP_XML, expected_year=2025, expected_volume=31)
    papers[1]["issue"] = "3"

    with pytest.raises(DblpCompletenessError, match="missing expected issues: 2"):
        validate_completeness(papers, html_article_count=2)


def test_dblp_outputs_preserve_all_records_and_summary(tmp_path):
    config = get_publication("tvcg2025")
    papers = parse_dblp_xml(DBLP_XML, expected_year=2025, expected_volume=31)
    paths = output_paths(tmp_path, config.key)
    summary = build_dblp_summary(config, papers, 2, paths)

    write_dblp_outputs(papers, paths, summary)

    assert paths.jsonl.read_text(encoding="utf-8").count("\n") == 2
    assert summary["source"] == "DBLP only"
    assert "four-digit homonym-disambiguation suffixes removed" in summary[
        "author_name_normalization"
    ]
    assert summary["representations_match"] is True
    assert summary["counts_by_issue"] == {"1": 1, "2": 1}
    assert summary["missing_required_fields"]["doi"] == 1
