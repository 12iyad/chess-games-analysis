"""Run full pipeline: fetch games → ingest events → reports (queen-loss + why losing)."""
import sys

from config import YEAR_FILTER
from fetch import run_fetch
from ingest import run_ingest
from report import run_queen_loss_report
from report_why_losing import run_why_losing_report


def main() -> None:
    if YEAR_FILTER is not None:
        print(f"Filtering to year {YEAR_FILTER} only.\n")
    print("Step 1: Fetching games from Chess.com...")
    n = run_fetch()
    print(f"  Stored {n} games.\n")

    if n == 0:
        print("No games to ingest. Exiting.")
        sys.exit(0)

    print("Step 2: Ingesting (parsing PGNs, detecting events, opening detection)...")
    m = run_ingest()
    print(f"  Processed {m} games.\n")

    print("Step 3: Queen-loss weakness report")
    run_queen_loss_report()

    print("Step 4: Why I'm losing (White vs Black, opening failure reasoning)")
    run_why_losing_report()


if __name__ == "__main__":
    main()
