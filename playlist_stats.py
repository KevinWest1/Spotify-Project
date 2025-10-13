# playlist_stats.py
import json
import os
from collections import Counter, defaultdict
from datetime import datetime

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Same playlists as gaming.py (order matters here!)
PLAYLISTS = {
    "ssssss": "4B7tWbwr8fspGOEuNzSFVd",
    "0.5": "3gjKqrz2I8Ex8Yh30WmG8B",
    "1": "6dfLHXWKCQKkb3zZnJvjJg",
    "2": "0lE4P0uoqvtNVAMCa8gTYP",
    "3": "1YRoyVyruSZWLNJo6eW3Rq"
}

# scoring weights
POINTS = {
    "ssssss": 1,
    "0.5": 3,
    "1": 10
}
MULTIPLIERS = {
    "2": 2,
    "3": 3
}

# ---------------- Helpers ----------------

def load_snapshot(playlist_id):
    filename = f"snapshot_{playlist_id}.json"
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as f:
        return json.load(f)

def extract_artist(song_str):
    if " - " in song_str:
        return song_str.rsplit(" - ", 1)[-1]
    return "Unknown"

def top_artists_for_playlist(name, playlist_id, top_n=10):
    tracks = load_snapshot(playlist_id)
    artists = [extract_artist(track["song"]) for track in tracks]
    counter = Counter(artists)
    return counter.most_common(top_n)

# ---------------- Yearly Adds ----------------

def load_yearly_logs():
    logs = defaultdict(list)
    for file in os.listdir():
        if file.startswith("playlist_log_") and file.endswith(".json"):
            try:
                year = int(file.split("_")[-1].split(".")[0])
            except ValueError:
                continue
            with open(file, "r") as f:
                raw = json.load(f)
            entries = []
            for iso_dt, line in raw:
                dt = datetime.fromisoformat(iso_dt)
                entries.append((dt, line))
            logs[year] = entries
    return logs

def most_added_artists_by_year(logs, top_n=3):
    results = defaultdict(dict)
    for year, entries in logs.items():
        counts_by_playlist = defaultdict(Counter)
        for dt, line in entries:
            if "was added to" in line:
                try:
                    song_part, rest = line.split(" was added to ")
                    playlist_name = rest.strip("'")
                    artist = extract_artist(song_part)
                    counts_by_playlist[playlist_name][artist] += 1
                except Exception:
                    continue
        for playlist_name, counter in counts_by_playlist.items():
            results[year][playlist_name] = counter.most_common(top_n)
    return results

# ---------------- Score Calculation ----------------

def compute_artist_scores():
    """
    Apply scoring system:
      - +1 per song in 'ssssss'
      - +3 per song in '0.5'
      - +10 per song in '1'
      






      - x2 multiplier if in '2'
      - x3 multiplier if in '3'
    """
    artist_points = defaultdict(int)
    artist_playlists = defaultdict(set)

    # count songs in additive playlists
    for playlist_name, playlist_id in PLAYLISTS.items():
        tracks = load_snapshot(playlist_id)
        for track in tracks:
            artist = extract_artist(track["song"])
            if playlist_name in POINTS:
                artist_points[artist] += POINTS[playlist_name]
            artist_playlists[artist].add(playlist_name)

    # apply multipliers
    final_scores = {}
    for artist, base_points in artist_points.items():
        score = base_points
        if "2" in artist_playlists[artist]:
            score *= 2
        if "3" in artist_playlists[artist]:
            score *= 3
        final_scores[artist] = score

    # sort descending
    sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores

# ---------------- PDF Export ----------------

def save_stats_pdf(stats, yearly_stats, scores, pdf_file="playlist_stats.pdf"):
    doc = SimpleDocTemplate(pdf_file, pagesize=LETTER)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        name="Header",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        spaceAfter=12
    )
    playlist_style = ParagraphStyle(
        name="PlaylistHeader",
        parent=styles["Heading2"],
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6
    )
    entry_style = ParagraphStyle(
        name="Entry",
        parent=styles["Normal"],
        alignment=TA_LEFT,
        spaceAfter=4
    )

    content = []

    # Section 1: Current Top 10 Artists
    content.append(Paragraph("Top 10 Artists per Playlist (Current Snapshot)", header_style))
    content.append(Spacer(1, 12))
    for playlist_name in PLAYLISTS.keys():
        artist_counts = stats.get(playlist_name, [])
        content.append(Paragraph(f"Playlist: {playlist_name}", playlist_style))
        for i, (artist, count) in enumerate(artist_counts, start=1):
            line = f"{i}. {artist}: {count} songs"
            content.append(Paragraph(line, entry_style))
        content.append(Spacer(1, 12))

    # Section 2: Yearly Most Added Artists
    content.append(Paragraph("Most Songs Added per Playlist by Year", header_style))
    content.append(Spacer(1, 12))
    for year in sorted(yearly_stats.keys()):
        content.append(Paragraph(f"Year: {year}", playlist_style))
        for playlist_name in PLAYLISTS.keys():
            top_artists = yearly_stats[year].get(playlist_name, [])
            if top_artists:
                content.append(Paragraph(f"{playlist_name}:", entry_style))
                for i, (artist, count) in enumerate(top_artists, start=1):
                    line = f"   {i}. {artist} ({count} songs added)"
                    content.append(Paragraph(line, entry_style))
        content.append(Spacer(1, 12))

    # Section 3: Top Artists by Score
    content.append(Paragraph("Top Artists by Score", header_style))
    content.append(Spacer(1, 12))
    for i, (artist, score) in enumerate(scores[:25], start=1):  # top 25
        line = f"{i}. {artist}: {score} points"
        content.append(Paragraph(line, entry_style))

    doc.build(content)
    print(f"PDF written to {pdf_file}")

# ---------------- Main ----------------

def main():
    # Part 1: Current snapshot stats
    stats = {}
    for name, playlist_id in PLAYLISTS.items():
        stats[name] = top_artists_for_playlist(name, playlist_id)

    # Part 2: Yearly added stats
    logs = load_yearly_logs()
    yearly_stats = most_added_artists_by_year(logs, top_n=3)

    # Part 3: Scoring system
    scores = compute_artist_scores()

    # Save everything into a PDF
    save_stats_pdf(stats, yearly_stats, scores)

if __name__ == "__main__":
    main()
