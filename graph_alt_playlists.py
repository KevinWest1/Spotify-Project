import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from collections import defaultdict

PLAYLISTS = {
    "Mildly Melancholic": "0hGEn1yjnLKYmeCbKGkr8P",
    "toned down": "5td6SohjLn6NeT27pUOkdO",
    "sincere": "4UVqPX3EI3rNaqaytocjRM",
    "feelin like shit": "0Nuq50XcGNsB97dD3q5xmO",
    "skate": "3B7wX5QGdFlYLQNuBMABqK",
    "New Wave, etc": "55ipBCMc3kpKuKEjhBTxYF",
    "Sunday Morning": "2kCJTYiQwZUdDqC44vHxx5",
    ".......": "4ueLJdur3HKCA4jAyqblDS",
    "nope": "5SJPA92ShNI4Kios7FAaLI",
    "me_irl": "4gwj3TKuOB6IW7JJ0PVGD8",
    "rock": "642d4xEKojPrfhkbiWQHvg",
    "L": "4GV6rHvhQ1Zj2UL7od4Vg1",
    "!": "2UJlsSZcvSNiNZMyEHKThC",
    "songs my mom might like": "4Dly3oLBjXDPolyq8wJiqB",
    "Songs that are Girls' Names": "4VRwiWcy2qPMaX8yCg4GU3",
    "()": "58hrOxHV0ICKKOrwRXtKyh",
    "yes?": "1b4gciYjdoV1LydDgW6FA7"
}


def backfill_from_logs(out_file="non_main_playlist_sizes.json"):
    history = []
    sizes = {name: 0 for name in PLAYLISTS.keys()}

    # Collect all entries across all years
    all_entries = []
    for fname in os.listdir("."):
        if fname.startswith("playlist_log_alt") and fname.endswith(".json"):
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

def plot_history(filename="non_main_playlist_sizes.json", out_file="non_main_playlist_sizes.png"):
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
    backfill_from_logs()   # one-time rebuild from log files
    plot_history()
