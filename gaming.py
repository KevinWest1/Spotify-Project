# gaming.py  -- single-file complete implementation
import os
import json
from datetime import datetime
import zoneinfo
from collections import defaultdict

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ---------------- Configuration ----------------
LOCAL_TZ = zoneinfo.ZoneInfo("America/Los_Angeles")

CLIENT_ID = "d582b750da684ad099b22626b07d431e"
CLIENT_SECRET = "afb3dbd59697452c8621dca95d645122"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-read-private",
    cache_path="token_cache.json"
))

PLAYLISTS = {
    "ssssss": "4B7tWbwr8fspGOEuNzSFVd",
    "0.5": "3gjKqrz2I8Ex8Yh30WmG8B",
    "1": "6dfLHXWKCQKkb3zZnJvjJg",
    "2": "0lE4P0uoqvtNVAMCa8gTYP",
    "3": "1YRoyVyruSZWLNJo6eW3Rq"
}

# ---------------- Helpers ----------------

def get_playlist_tracks(sp, playlist_id):
    """Fetch all tracks in a playlist, returning list of dicts: {'song','added_at'}"""
    tracks = []
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results['items']:
            track = item.get('track')
            if track:
                song = f"{track.get('name')} - {track.get('artists')[0].get('name')}"
                tracks.append({
                    "song": song,
                    "added_at": item.get("added_at")  # ISO string (UTC) or None
                })
        if results.get('next'):
            results = sp.next(results)
        else:
            break
    return tracks

def load_previous_tracks(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_current_tracks(tracks, filename):
    with open(filename, "w") as f:
        json.dump(tracks, f)

def format_date(iso_string):
    """Return (pretty_date_string, tz-aware-datetime) from Spotify ISO time (UTC)."""
    # iso_string example: "2025-02-24T15:32:11Z"
    dt_utc = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    dt_local = dt_utc.astimezone(LOCAL_TZ)
    # returned pretty string isn't used for PDF header (we build header from date)
    return dt_local.strftime("%A, %m/%d/%y"), dt_local

# ---------------- Logging storage (JSON + PDF) ----------------

def load_existing_entries(year):
    """Load existing (dt,line) entries for a year from the JSON sidecar file."""
    json_file = f"playlist_log_{year}.json"
    if not os.path.exists(json_file):
        return []
    with open(json_file, "r") as f:
        raw = json.load(f)
    entries = []
    for iso_dt, line in raw:
        # datetime.fromisoformat supports timezone offset if present
        dt = datetime.fromisoformat(iso_dt)
        entries.append((dt, line))
    return entries

def save_entries(year, entries, summary_override=None):
    """Save year entries to JSON and generate the PDF with a complete summary."""
    # Save JSON (keeps full history of the year)
    json_file = f"playlist_log_{year}.json"
    with open(json_file, "w") as f:
        json.dump([(dt.isoformat(), line) for dt, line in entries], f)

    # Build summary fresh from ALL entries
    summary = defaultdict(lambda: {"added": 0, "removed": 0})
    for _, line in entries:
        for playlist_name in PLAYLISTS.keys():
            if f"'{playlist_name}'" in line:
                if "was added" in line:
                    summary[playlist_name]["added"] += 1
                elif "was removed" in line:
                    summary[playlist_name]["removed"] += 1

    # Write PDF with summary included
    pdf_file = f"playlist_log_{year}.pdf"
    write_entries_grouped_pdf(entries, pdf_file, summary)



def write_entries_grouped_pdf(entries, pdf_file, summary=None):
    """Write entries grouped by date, nicely formatted in a PDF, with summary at bottom."""
    grouped = {}
    for dt, line in entries:
        day = dt.date()
        if day not in grouped:
            grouped[day] = []
        grouped[day].append(line)

    doc = SimpleDocTemplate(pdf_file, pagesize=LETTER)
    styles = getSampleStyleSheet()

    date_style = ParagraphStyle(
        name="DateHeader",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        spaceAfter=12
    )
    entry_style = ParagraphStyle(
        name="Entry",
        parent=styles["Normal"],
        alignment=TA_LEFT,
        spaceAfter=6
    )
    summary_header_style = ParagraphStyle(
        name="SummaryHeader",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        spaceBefore=24,
        spaceAfter=12
    )

    content = []

    for day in sorted(grouped.keys()):
        pretty_date = day.strftime("%A, %B %d, %Y")
        content.append(Paragraph(pretty_date, date_style))
        content.append(Spacer(1, 6))

        for line in grouped[day]:
            content.append(Paragraph(line, entry_style))
        content.append(Spacer(1, 12))

    # Always add summary at bottom
    if summary:
        content.append(Spacer(1, 24))
        content.append(Paragraph("Year-to-Date Playlist Summary", summary_header_style))
        for playlist, counts in summary.items():
            line = f"'{playlist}': {counts['added']} added, {counts['removed']} removed"
            content.append(Paragraph(line, entry_style))

    doc.build(content)
    print(f"PDF log written to {pdf_file}")


# ---------------- Core change detection ----------------

def log_changes(old, new, playlist_name):
    """
    Compare old/new snapshots (lists of dicts).
    Return (new_entries, counts) where:
      new_entries = [(dt, line), ...]
      counts = {"added": N, "removed": M}
    """
    old_songs = {track["song"] for track in old}
    new_songs = {track["song"] for track in new}

    added = [track for track in new if track["song"] not in old_songs]
    removed = [track for track in old if track["song"] not in new_songs]

    new_entries = []
    counts = {"added": 0, "removed": 0}

    # Additions: use Spotify's added_at timestamp (converted to local tz)
    for track in added:
        added_at = track.get("added_at")
        if added_at:
            _, dt = format_date(added_at)
        else:
            dt = datetime.now(LOCAL_TZ)
        new_entries.append((dt, f"{track['song']} was added to '{playlist_name}'"))
    counts["added"] = len(added)

    # Removals: we only know the moment we discovered them
    now = datetime.now(LOCAL_TZ)
    for track in removed:
        new_entries.append((now, f"{track['song']} was removed from '{playlist_name}'"))
    counts["removed"] = len(removed)

    return new_entries, counts

# ---------------- Backfill (run ONCE) ----------------

def backfill_log(sp, playlists):
    """Pull full added_at history from Spotify and build yearly JSON+PDF files."""
    all_entries = []
    for name, playlist_id in playlists.items():
        tracks = get_playlist_tracks(sp, playlist_id)
        for track in tracks:
            if track.get("added_at"):
                _, dt = format_date(track["added_at"])
                all_entries.append((dt, f"{track['song']} was added to '{name}'"))
    all_entries.sort(key=lambda x: x[0])

    # group by year
    entries_by_year = defaultdict(list)
    for dt, line in all_entries:
        entries_by_year[dt.year].append((dt, line))

    # save per year (overwrites existing year data — good for initial boot)
    for year, entries in entries_by_year.items():
        save_entries(year, entries)
    print("Backfill complete. Yearly JSON + PDFs written.")

# ---------------- Main flow (incremental) ----------------

def main_incremental():
    # collect new entries across playlists in this run
    all_new_entries = []
    # track per-year, per-playlist counts for summary
    summary_by_year = defaultdict(lambda: defaultdict(lambda: {"added": 0, "removed": 0}))

    for name, playlist_id in PLAYLISTS.items():
        snapshot_file = f"snapshot_{playlist_id}.json"
        old_tracks = load_previous_tracks(snapshot_file)
        current_tracks = get_playlist_tracks(sp, playlist_id)

        new_entries, counts = log_changes(old_tracks, current_tracks, name)

        # extend global list
        all_new_entries.extend(new_entries)

        # update per-year summary by inspecting each new entry's dt and text
        for dt, line in new_entries:
            year = dt.year
            if "was added" in line:
                summary_by_year[year][name]["added"] += 1
            elif "was removed" in line:
                summary_by_year[year][name]["removed"] += 1

        # save snapshot for next run
        save_current_tracks(current_tracks, snapshot_file)

    # group new entries by year and merge with historical JSONs
    entries_by_year = defaultdict(list)
    for dt, line in all_new_entries:
        entries_by_year[dt.year].append((dt, line))

    for year, new_entries in entries_by_year.items():
        # load existing history
        existing = load_existing_entries(year)  # list of (dt,line)
        # merge and dedupe (use iso-string + line as key)
        merged_map = {}
        for dt, line in existing + new_entries:
            key = (dt.isoformat(), line)
            merged_map[key] = (dt, line)
        merged = list(merged_map.values())
        merged.sort(key=lambda x: x[0])

        # combine summary (merge counts for this year)
        summary_for_year = summary_by_year.get(year, {})
        # If you want to include counts from existing history,
        # you'd have to scan existing lines; for now summary_for_year includes counts from this run.

        # save json and regenerate PDF
        save_entries(year, merged, summary_for_year)

    print("Incremental run complete. Yearly JSON + PDFs updated.")

# ---------------- Run control ----------------

if __name__ == "__main__":
    # 1) If you haven't done a full historical backfill yet, run this ONCE:
    #backfill_log(sp, PLAYLISTS); #then comment it out after a successful run.

    # 2) Afterwards (normally), run incremental update:
    main_incremental()
