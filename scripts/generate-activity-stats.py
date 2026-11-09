#!/usr/bin/env python3
"""Generate light and dark activity cards from GitHub's public contribution calendar."""

from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {
    "dark": ROOT / "assets" / "activity-stats-dark.svg",
    "light": ROOT / "assets" / "activity-stats-light.svg",
}
CALENDAR_URL = "https://github.com/users/gowrishZeeve/contributions"


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.total_heading = False
        self.heading_text = []
        self.days = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2" and attrs.get("id") == "js-contribution-activity-description":
            self.total_heading = True
        if tag == "td" and "ContributionCalendar-day" in attrs.get("class", "").split():
            day = attrs.get("data-date")
            level = attrs.get("data-level")
            if day and level and level.isdigit():
                self.days[date.fromisoformat(day)] = int(level)

    def handle_endtag(self, tag):
        if tag == "h2" and self.total_heading:
            self.total_heading = False

    def handle_data(self, data):
        if self.total_heading:
            self.heading_text.append(data.strip())


def fetch_calendar():
    request = Request(
        CALENDAR_URL,
        headers={"User-Agent": "gowrishZeeve-profile-readme/1.0", "Accept": "text/html"},
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub contribution calendar returned HTTP {response.status}")
        page = response.read().decode("utf-8", errors="replace")

    parser = CalendarParser()
    parser.feed(page)
    heading = " ".join(part for part in parser.heading_text if part)
    match = re.search(r"([\d,]+)\s+contributions?\s+in the last year", heading, re.IGNORECASE)
    if not match or not parser.days:
        raise RuntimeError("Could not read the contribution total and daily calendar from GitHub")
    return int(match.group(1).replace(",", "")), parser.days


def streaks(days):
    active_dates = sorted(day for day, level in days.items() if level > 0)
    if not active_dates:
        return 0, 0

    longest = current = 1
    for previous, day in zip(active_dates, active_dates[1:]):
        if day == previous + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    today = datetime.now(timezone.utc).date()
    anchor = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    current_streak = 0
    while days.get(anchor, 0) > 0:
        current_streak += 1
        anchor -= timedelta(days=1)
    return current_streak, longest


def svg_card(total, current, longest, days, theme):
    dark = theme == "dark"
    palette = {
        "bg": "#101820" if dark else "#F7FAF8",
        "border": "#26363D" if dark else "#DCE8E1",
        "heading": "#F3F7F5" if dark else "#17251E",
        "text": "#AABBB5" if dark else "#66766D",
        "accent": "#55D187" if dark else "#16834A",
        "levels": (
            ["#23343A", "#193C2D", "#1F6E48", "#2B9C64", "#55D187"]
            if dark
            else ["#E8F2EB", "#C6E9D1", "#8BD4A3", "#4EAF70", "#197A43"]
        ),
    }

    first_day = min(days)
    last_day = max(days)
    grid_start = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    week_count = (last_day - grid_start).days // 7 + 1
    cell = 8
    gap = 3
    grid_x = 493
    grid_y = 94

    squares = []
    for day, level in days.items():
        offset = (day - grid_start).days
        week = offset // 7
        row = (day.weekday() + 1) % 7
        x = grid_x + week * (cell + gap)
        y = grid_y + row * (cell + gap)
        color = palette["levels"][min(max(level, 0), 4)]
        squares.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}" />')

    grid_width = week_count * (cell + gap) - gap
    card_width = max(1080, grid_x + grid_width + 36)
    month_labels = []
    seen_months = set()
    for day in sorted(days):
        if day.day <= 7 and day.month not in seen_months:
            seen_months.add(day.month)
            offset = (day - grid_start).days
            week = offset // 7
            x = grid_x + week * (cell + gap)
            month_labels.append(
                f'<text x="{x}" y="82" fill="{palette["text"]}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="10">{day.strftime("%b").upper()}</text>'
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="210" viewBox="0 0 {card_width} 210" role="img" aria-labelledby="title description">
  <title id="title">GitHub activity summary</title>
  <desc id="description">{total:,} contributions in the last year, a current streak of {current} days, and a longest streak of {longest} days. Daily activity is anonymized.</desc>
  <rect x="1" y="1" width="{card_width - 2}" height="208" rx="18" fill="{palette['bg']}" stroke="{palette['border']}" stroke-width="1" />
  <text x="34" y="43" fill="{palette['heading']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16" font-weight="700" letter-spacing="1.6">GITHUB ACTIVITY</text>
  <text x="34" y="64" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11" letter-spacing="0.8">PUBLIC + PRIVATE · ANONYMIZED</text>
  <text x="34" y="117" fill="{palette['accent']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="700">{total:,}</text>
  <text x="34" y="139" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11" letter-spacing="0.6">CONTRIBUTIONS</text>
  <line x1="171" y1="91" x2="171" y2="151" stroke="{palette['border']}" />
  <text x="194" y="117" fill="{palette['heading']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="700">{current}</text>
  <text x="194" y="139" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11" letter-spacing="0.6">CURRENT STREAK</text>
  <line x1="346" y1="91" x2="346" y2="151" stroke="{palette['border']}" />
  <text x="369" y="117" fill="{palette['heading']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="28" font-weight="700">{longest}</text>
  <text x="369" y="139" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11" letter-spacing="0.6">LONGEST STREAK</text>
  <text x="{grid_x}" y="63" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="10" letter-spacing="0.8">CONTRIBUTION CALENDAR</text>
  {''.join(month_labels)}
  {''.join(squares)}
  <text x="34" y="183" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="10">Updated daily from GitHub's public contribution calendar</text>
</svg>
'''


def main():
    total, days = fetch_calendar()
    current, longest = streaks(days)
    for theme, path in OUTPUTS.items():
        path.write_text(svg_card(total, current, longest, days, theme), encoding="utf-8")
    print(f"Updated activity cards for {len(days)} days")


if __name__ == "__main__":
    main()
