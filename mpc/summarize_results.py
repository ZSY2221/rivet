from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

PATTERN = re.compile(r"rivet_screen-(\d+)-(\d+)-(\d+)_rtt([\d.]+)ms\.log$")


def parse(path: Path):
    match = PATTERN.match(path.name)
    if not match:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    online = re.search(
        r"Spent ([\d.]+) seconds \(([\d.]+) MB, (\d+) rounds[^)]*\) on the online phase",
        text,
    )
    offline = re.search(
        r"and ([\d.]+) seconds \(([\d.]+) MB, (\d+) rounds[^)]*\) on the preprocessing/offline phase",
        text,
    )
    total = re.search(r"Time = ([\d.]+) seconds", text)
    traffic = re.search(r"Global data sent = ([\d.]+) MB", text)
    if not online:
        online = re.search(
            r"online_s=([\d.]+) online_one_party_mb=([\d.]+) online_rounds=(\d+)",
            text,
        )
    if not offline:
        offline = re.search(
            r"offline_s=([\d.]+) offline_one_party_mb=([\d.]+) offline_rounds=(\d+)",
            text,
        )
    if not total:
        total = re.search(r"end_to_end_s=([\d.]+)", text)
    if not traffic:
        traffic = re.search(r"end_to_end_server_total_mb=([\d.]+)", text)
    if not all((online, offline, total, traffic)):
        raise ValueError(path)
    d, L, k, rtt = match.groups()
    return {
        "d": int(d),
        "L": int(L),
        "k_sk": int(k),
        "rtt_ms": float(rtt),
        "online_s": float(online.group(1)),
        "online_one_party_mb": float(online.group(2)),
        "online_server_total_mb": 2 * float(online.group(2)),
        "online_rounds": int(online.group(3)),
        "offline_s": float(offline.group(1)),
        "offline_one_party_mb": float(offline.group(2)),
        "offline_rounds": int(offline.group(3)),
        "end_to_end_s": float(total.group(1)),
        "end_to_end_server_total_mb": float(traffic.group(1)),
        "source_log": path.name,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("mpc/results"))
    parser.add_argument("--output", type=Path, default=Path("mpc/results/screening_summary.csv"))
    args = parser.parse_args()
    rows = [parse(path) for path in sorted(args.input_dir.glob("rivet_screen-*_rtt*ms.log"))]
    rows = [row for row in rows if row]
    if not rows:
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
