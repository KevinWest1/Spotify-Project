import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from collections import defaultdict

PLAYLISTS = {
    "ssssss": "4B7tWbwr8fspGOEuNzSFVd",
    "0.5": "3gjKqrz2I8Ex8Yh30WmG8B",
    "1": "6dfLHXWKCQKkb3zZnJvjJg",
    "2": "0lE4P0uoqvtNVAMCa8gTYP",
    "3": "1YRoyVyruSZWLNJo6eW3Rq"
}


def backfill_from_logs(out_file="playlist_sizes.json"):
    history = []
    sizes = {name: 0 for name in PLAYLISTS.keys()}

    # Collect all entries across all years
    all_entries = []
    for fname in os.listdir("."):
        if fname.startswith("playlist_log_") and fname.endswith(".json"):
            with open(fname, "r") as f:
                raw = json.load(f)
                for iso_dt, line in raw:
                    dt = datetime.fromisoformat(iso_dt)
                    all_entries.append((dt, line))

    # Sort chronologically
    all_entries.sort(key=lambda x: x[0])

    # Replay history
    for dt, line in all_entries:
        for playlist_name in PLAYLISTS.keys():
            if f"'{playlist_name}'" in line:
                if "was added" in line:
                    sizes[playlist_name] += 1
                elif "was removed" in line:
                    sizes[playlist_name] -= 1
                history.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "playlist": playlist_name,
                    "count": sizes[playlist_name]
                })

    with open(out_file, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Backfilled history written to {out_file}")

def plot_history(filename="playlist_sizes.json", out_file="playlist_sizes.png"):
    if not os.path.exists(filename):
        print("No history file found. Run backfill_from_logs() first.")
        return

    with open(filename, "r") as f:
        history = json.load(f)

    # Organize by playlist
    data = defaultdict(list)
    for entry in history:
        date = datetime.strptime(entry["date"], "%Y-%m-%d")
        data[entry["playlist"]].append((date, entry["count"]))

    # Plot
    plt.figure(figsize=(10,6))
    for name, points in data.items():
        points.sort(key=lambda x: x[0])
        dates = [p[0] for p in points]
        counts = [p[1] for p in points]
        plt.plot(dates, counts, marker="o", label=name)

    plt.title("Playlist Sizes Over Time")
    plt.xlabel("Date")
    plt.ylabel("Number of Songs")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_file)
    print(f"Graph saved to {out_file}")

if __name__ == "__main__":
    #backfill_from_logs()   # one-time rebuild from log files
    plot_history()
