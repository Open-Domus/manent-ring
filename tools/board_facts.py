"""Print the numbers that the documents and the quote request quote about the board."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def facts() -> dict:
    out = ROOT / "electrical" / "out"
    board, routes = json.loads((out / "board.json").read_text()), json.loads((out / "routes.json").read_text())
    span = [v["l2"] - v["l1"] for v in routes["vias"]]
    ys = [y for _, y in board["outline"]]
    lo, hi, _ = board["tail_cut"]
    return {
        "strip": f"{board['length']} x {board['width']}",
        "tail": f"{round(hi - lo, 2)} x {round(max(ys) - board['width'] / 2, 2)}",
        "rigid areas": sum(z["kind"] == "rigid" for z in board["zones"]),
        "bends": sum(z["kind"] == "bend" for z in board["zones"]),
        "layers": board["layers"],
        "footprints": len(board["parts"]),
        "parts to place": sum(1 for p in board["parts"] if not p["dnp"] and not p["footprint"].startswith(("Pad_", "Cell_"))),
        "tracks": len(routes["tracks"]),
        "copper mm": round(sum(math.dist(a, b) for t in routes["tracks"] for a, b in zip(t["pts"], t["pts"][1:]))),
        "vias": len(span),
        "vias, adjacent layers": sum(s == 1 for s in span),
        "vias, stacked": sum(1 < s < board["layers"] - 1 for s in span),
        "vias, through all layers": sum(s == board["layers"] - 1 for s in span),
        "open connections": len(routes["failed"]),
    }


if __name__ == "__main__":
    for k, v in facts().items():
        print(f"{k:<26} {v}")
