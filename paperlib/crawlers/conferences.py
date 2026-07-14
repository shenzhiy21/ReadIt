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


CONFERENCES = {
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
    )
}


def get_conference(key):
    try:
        return CONFERENCES[key]
    except KeyError as error:
        known = ", ".join(sorted(CONFERENCES))
        raise KeyError(f"Unknown conference '{key}'. Known conferences: {known}") from error
