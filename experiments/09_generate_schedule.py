from unapproved_sum.schedule import SCHEDULE_PATH, validate_schedule, write_schedule


def main() -> None:
    path = write_schedule(SCHEDULE_PATH)
    errors = validate_schedule(path)
    if errors:
        print("SCHEDULE: FAIL")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("SCHEDULE: PASS")
    print("Wrote", path)


if __name__ == "__main__":
    main()
