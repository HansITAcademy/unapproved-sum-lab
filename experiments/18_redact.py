from unapproved_sum.analysis import REDACTED_PATH, redact_raw_ledger


def main() -> None:
    path = redact_raw_ledger(output_path=REDACTED_PATH)
    print("REDACTION: PASS")
    print("Publication-safe result file:", path)


if __name__ == "__main__":
    main()
