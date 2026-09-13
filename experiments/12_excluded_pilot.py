import argparse

from unapproved_sum.pilot import PILOT_PATH, build_pilot_cells, run_excluded_pilot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Acknowledge that this makes live paid API calls.")
    args = parser.parse_args()
    if not args.live:
        print(f"Pilot is {len(build_pilot_cells())} live trajectories and is excluded from analysis.")
        print("Re-run with --live when all three API keys are set.")
        raise SystemExit(2)
    path = run_excluded_pilot(PILOT_PATH)
    print("EXCLUDED PILOT COMPLETE:", path)
    print("It is safe to inspect this pilot because it is not part of the confirmatory sample.")


if __name__ == "__main__":
    main()
