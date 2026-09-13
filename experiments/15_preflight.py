import argparse

from unapproved_sum.confirmatory import validate_live_readiness


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-tag", action="store_true", help="Also require the ready tag and live API keys.")
    args = parser.parse_args()
    errors = validate_live_readiness(require_tag=args.require_tag)
    if errors:
        print("PREFLIGHT: FAIL")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("PREFLIGHT: PASS")


if __name__ == "__main__":
    main()
