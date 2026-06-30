from dataclasses import dataclass


@dataclass(frozen=True)
class OpenReviewConference:
    key: str
    invitation: str
    venues: tuple[str, ...]
    venueid: str | None = None


CONFERENCES = {
    "icml2026": OpenReviewConference(
        key="icml2026",
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
