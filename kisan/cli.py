"""python -m kisan.cli seed | run F001 [--question ...] [--offline] | eval [--offline]"""
import argparse
import json

from . import config


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed")
    r = sub.add_parser("run")
    r.add_argument("farmer_id")
    r.add_argument("--question")
    r.add_argument("--offline", action="store_true")
    e = sub.add_parser("eval")
    e.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    if a.cmd == "seed":
        from . import db
        print(f"Seeded {db.seed()} synthetic farmers into {config.DB_PATH}")
    elif a.cmd == "run":
        if a.offline:
            config.OFFLINE = True
        from .crew import run_pipeline
        rep = run_pipeline(a.farmer_id, a.question)
        print(json.dumps(rep.model_dump(), indent=2, ensure_ascii=False))
    else:
        from .evaluate import main as ev
        ev(a.offline)


if __name__ == "__main__":
    main()