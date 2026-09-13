from unapproved_sum.confirmatory import RAW_LEDGER_PATH, validate_raw_ledger


def main() -> None:
    errors = validate_raw_ledger(RAW_LEDGER_PATH)
    if errors:
        print("LEDGER VALIDATION: FAIL")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("LEDGER VALIDATION: PASS")
    print("Raw ledger:", RAW_LEDGER_PATH)


if __name__ == "__main__":
    main()
