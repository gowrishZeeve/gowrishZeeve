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
    "dark-mobile": ROOT / "assets" / "activity-stats-dark-mobile.svg",
    "light-mobile": ROOT / "assets" / "activity-stats-light-mobile.svg",
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
    mobile = theme.endswith("-mobile")
    dark = theme.startswith("dark")
    palette = {
        "bg": "#17241D" if dark else "#F2F0E7",
        "rule": "#647568" if dark else "#9AA597",
        "heading": "#F2F0E7" if dark else "#243227",
        "text": "#C2C9BC" if dark else "#536453",
        "accent": "#75D29A" if dark else "#176B43",
        "teal": "#63C8AC" if dark else "#14796F",
        "levels": (
            ["#27352C", "#244B32", "#286943", "#40945F", "#75D29A"]
            if dark
            else ["#E2E6D9", "#CDDCC8", "#A4CDA7", "#6EAA78", "#287343"]
        ),
    }

    first_day = min(days)
    last_day = max(days)
    grid_start = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    week_count = (last_day - grid_start).days // 7 + 1
    cell, gap = (5, 2) if mobile else (11, 4)
    grid_y = 204 if mobile else 247
    grid_width = week_count * (cell + gap) - gap
    card_width = 390 if mobile else max(900, grid_width + 72)
    grid_x = (card_width - grid_width) // 2 if mobile else 32

    squares = []
    for day, level in days.items():
        offset = (day - grid_start).days
        week = offset // 7
        row = (day.weekday() + 1) % 7
        x = grid_x + week * (cell + gap)
        y = grid_y + row * (cell + gap)
        color = palette["levels"][min(max(level, 0), 4)]
        squares.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="1" fill="{color}" />')

    month_labels = []
    seen_months = set()
    for day in sorted(days):
        if day.day <= 7 and day.month not in seen_months:
            seen_months.add(day.month)
            offset = (day - grid_start).days
            week = offset // 7
            x = grid_x + week * (cell + gap)
            if mobile:
                x = min(x, card_width - 32)
            month_y = 194 if mobile else 235
            month_size = 9 if mobile else 13
            month_labels.append(
                f'<text x="{x}" y="{month_y}" fill="{palette["text"]}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="{month_size}" font-weight="600" letter-spacing="0.15">{day.strftime("%b").upper()}</text>'
            )

    if mobile:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="390" height="355" viewBox="0 0 390 355" role="img" aria-labelledby="title description">
  <title id="title">GitHub activity summary</title>
  <desc id="description">{total:,} contributions in the last year, a current streak of {current} days, and a longest streak of {longest} days. Daily activity is anonymized.</desc>
  <rect width="390" height="355" fill="{palette['bg']}" />
  <text x="20" y="37" fill="{palette['heading']}" font-family="Georgia, 'Times New Roman', serif" font-size="18" font-weight="700">GitHub activity</text>
  <text x="20" y="57" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9" letter-spacing="0.2">PUBLIC + PRIVATE · ANONYMIZED</text>
  <text x="370" y="37" text-anchor="end" fill="{palette['teal']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9" font-weight="700" letter-spacing="0.7">LAST 12 MONTHS</text>
  <line x1="20" y1="72" x2="370" y2="72" stroke="{palette['rule']}" stroke-width="1" />

  <text x="22" y="111" fill="{palette['accent']}" font-family="Georgia, 'Times New Roman', serif" font-size="27" font-weight="700">{total:,}</text>
  <text x="22" y="131" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9" font-weight="600" letter-spacing="0.35">CONTRIBUTIONS</text>
  <line x1="139" y1="85" x2="139" y2="137" stroke="{palette['rule']}" stroke-width="1" />

  <text x="153" y="111" fill="{palette['heading']}" font-family="Georgia, 'Times New Roman', serif" font-size="27" font-weight="700">{current}</text>
  <text x="153" y="131" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9" font-weight="600" letter-spacing="0.25">CURRENT STREAK</text>
  <line x1="267" y1="85" x2="267" y2="137" stroke="{palette['rule']}" stroke-width="1" />

  <text x="281" y="111" fill="{palette['heading']}" font-family="Georgia, 'Times New Roman', serif" font-size="27" font-weight="700">{longest}</text>
  <text x="281" y="131" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9" font-weight="600" letter-spacing="0.2">LONGEST STREAK</text>

  <line x1="20" y1="151" x2="370" y2="151" stroke="{palette['rule']}" stroke-width="1" />
  <text x="20" y="176" fill="{palette['heading']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="0.55">CONTRIBUTION CALENDAR</text>
  {''.join(month_labels)}
  {''.join(squares)}
  <line x1="20" y1="265" x2="370" y2="265" stroke="{palette['rule']}" stroke-width="1" />
  <text x="20" y="286" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9">Updated daily from GitHub's public contribution calendar</text>
  <g transform="translate(261 314)" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="9" fill="{palette['text']}">
    <text x="0" y="8">Less</text>
    <rect x="28" y="0" width="7" height="7" rx="1" fill="{palette['levels'][0]}" />
    <rect x="38" y="0" width="7" height="7" rx="1" fill="{palette['levels'][1]}" />
    <rect x="48" y="0" width="7" height="7" rx="1" fill="{palette['levels'][2]}" />
    <rect x="58" y="0" width="7" height="7" rx="1" fill="{palette['levels'][3]}" />
    <rect x="68" y="0" width="7" height="7" rx="1" fill="{palette['levels'][4]}" />
    <text x="82" y="8">More</text>
  </g>
</svg>
'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="390" viewBox="0 0 {card_width} 390" role="img" aria-labelledby="title description">
  <title id="title">GitHub activity summary</title>
  <desc id="description">{total:,} contributions in the last year, a current streak of {current} days, and a longest streak of {longest} days. Daily activity is anonymized.</desc>
  <rect width="{card_width}" height="390" fill="{palette['bg']}" />
  <text x="32" y="48" fill="{palette['heading']}" font-family="Georgia, 'Times New Roman', serif" font-size="23" font-weight="700" letter-spacing="0.1">GitHub activity</text>
  <text x="32" y="72" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" letter-spacing="0.45">PUBLIC + PRIVATE · ANONYMIZED</text>
  <text x="{card_width - 32}" y="51" text-anchor="end" fill="{palette['teal']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" font-weight="700" letter-spacing="1.1">LAST 12 MONTHS</text>
  <line x1="32" y1="88" x2="{card_width - 32}" y2="88" stroke="{palette['rule']}" stroke-width="1" />

  <text x="42" y="137" fill="{palette['accent']}" font-family="Georgia, 'Times New Roman', serif" font-size="37" font-weight="700">{total:,}</text>
  <text x="42" y="162" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" letter-spacing="0.7">CONTRIBUTIONS</text>
  <line x1="300" y1="105" x2="300" y2="168" stroke="{palette['rule']}" stroke-width="1" />

  <text x="330" y="137" fill="{palette['heading']}" font-family="Georgia, 'Times New Roman', serif" font-size="37" font-weight="700">{current}</text>
  <text x="330" y="162" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" letter-spacing="0.55">CURRENT STREAK</text>
  <line x1="588" y1="105" x2="588" y2="168" stroke="{palette['rule']}" stroke-width="1" />

  <text x="618" y="137" fill="{palette['heading']}" font-family="Georgia, 'Times New Roman', serif" font-size="37" font-weight="700">{longest}</text>
  <text x="618" y="162" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" letter-spacing="0.55">LONGEST STREAK</text>

  <line x1="32" y1="184" x2="{card_width - 32}" y2="184" stroke="{palette['rule']}" stroke-width="1" />
  <text x="32" y="213" fill="{palette['heading']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14" font-weight="700" letter-spacing="0.85">CONTRIBUTION CALENDAR</text>

  {''.join(month_labels)}
  {''.join(squares)}
  <line x1="32" y1="354" x2="{card_width - 32}" y2="354" stroke="{palette['rule']}" stroke-width="1" />
  <text x="32" y="375" fill="{palette['text']}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12">Updated daily from GitHub's public contribution calendar</text>
  <g transform="translate({card_width - 160} 361)" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="11" fill="{palette['text']}">
    <text x="0" y="9">Less</text>
    <rect x="31" y="0" width="10" height="10" rx="3" fill="{palette['levels'][0]}" />
    <rect x="45" y="0" width="10" height="10" rx="3" fill="{palette['levels'][1]}" />
    <rect x="59" y="0" width="10" height="10" rx="3" fill="{palette['levels'][2]}" />
    <rect x="73" y="0" width="10" height="10" rx="3" fill="{palette['levels'][3]}" />
    <rect x="87" y="0" width="10" height="10" rx="3" fill="{palette['levels'][4]}" />
    <text x="104" y="9">More</text>
  </g>
</svg>
'''


def main():
    total, days = fetch_calendar()
    current, longest = streaks(days)
    for variant, path in OUTPUTS.items():
        path.write_text(svg_card(total, current, longest, days, variant), encoding="utf-8")
    print(f"Updated activity cards for {len(days)} days")


if __name__ == "__main__":
    main()
