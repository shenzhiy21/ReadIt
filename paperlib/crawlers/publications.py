from dataclasses import dataclass


@dataclass(frozen=True)
class OpenReviewConference:
    key: str
    name: str
    invitation: str
    venues: tuple[str, ...]
    venueid: str | None = None
    fallback_jsonl_url: str | None = None
    fallback_status_venues: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class DblpJournalVolume:
    key: str
    name: str
    year: int
    volume: int
    expected_issues: tuple[str, ...]
    html_url: str
    xml_url: str


def _tvcg_volume(year, volume, complete=True):
    expected_issues = tuple(str(issue) for issue in range(1, 13)) if complete else ()
    base_url = f"https://dblp.org/db/journals/tvcg/tvcg{volume}"
    return DblpJournalVolume(
        key=f"tvcg{year}",
        name=f"TVCG {year}",
        year=year,
        volume=volume,
        expected_issues=expected_issues,
        html_url=f"{base_url}.html",
        xml_url=f"{base_url}.xml",
    )


PUBLICATIONS = {
    "tvcg2023": _tvcg_volume(2023, 29),
    "tvcg2024": _tvcg_volume(2024, 30),
    "tvcg2025": _tvcg_volume(2025, 31),
    # The 2026 volume is still in progress. Validate issue continuity through
    # the latest issue currently indexed by DBLP instead of requiring 1-12.
    "tvcg2026": _tvcg_volume(2026, 32, complete=False),
    "iclr2026": OpenReviewConference(
        key="iclr2026",
        name="ICLR 2026",
        invitation="ICLR.cc/2026/Conference/-/Submission",
        venues=(
            "ICLR 2026 Poster",
            "ICLR 2026 Spotlight",
            "ICLR 2026 Oral",
        ),
        venueid="ICLR.cc/2026/Conference",
        fallback_jsonl_url=(
            "https://raw.githubusercontent.com/papercopilot/openreview/main/"
            "venues/iclr/iclr2026.jsonl"
        ),
        fallback_status_venues=(
            ("Poster", "ICLR 2026 Poster"),
            ("SPOT", "ICLR 2026 Spotlight"),
            ("Oral", "ICLR 2026 Oral"),
        ),
    ),
    "icml2026": OpenReviewConference(
        key="icml2026",
        name="ICML 2026",
        invitation="ICML.cc/2026/Conference/-/Submission",
        venues=(
            "ICML 2026 oral",
            "ICML 2026 spotlight",
            "ICML 2026 regular",
        ),
        venueid="ICML.cc/2026/Conference",
    ),
}


def get_publication(key):
    try:
        return PUBLICATIONS[key]
    except KeyError as error:
        known = ", ".join(sorted(PUBLICATIONS))
        raise KeyError(
            f"Unknown publication '{key}'. Known publications: {known}"
        ) from error
