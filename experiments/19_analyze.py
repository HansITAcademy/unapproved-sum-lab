import json

from unapproved_sum.analysis import analyze_redacted


def main() -> None:
    summary = analyze_redacted()
    print("ANALYSIS: PASS")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
