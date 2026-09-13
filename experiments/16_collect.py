import argparse

from unapproved_sum.confirmatory import CONFIRMATION_PHRASE, RAW_LEDGER_PATH, collect_confirmatory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if not args.live or args.confirm != CONFIRMATION_PHRASE:
        print("This command starts the evidentiary API collection.")
        print("Required confirmation:", CONFIRMATION_PHRASE)
        raise SystemExit(2)
    path = collect_confirmatory(path=RAW_LEDGER_PATH, resume=args.resume)
    print("COLLECTION TERMINAL:", path)
    print("Now validate the ledger before opening or analyzing behavioral outcomes.")


if __name__ == "__main__":
    main()
