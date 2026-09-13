from unapproved_sum.manifest import MANIFEST_PATH, validate_manifest, write_manifest
from unapproved_sum.protocol import expected_trajectory_count, openai_replication_count


def main() -> None:
    payload = write_manifest(MANIFEST_PATH)
    errors = validate_manifest(MANIFEST_PATH)
    if errors:
        print("FREEZE: FAIL")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("FREEZE MANIFEST: PASS")
    print("Manifest:", MANIFEST_PATH)
    print("OpenAI replication subset:", openai_replication_count())
    print("Total confirmatory trajectories:", expected_trajectory_count())
    print("Next: commit this state, create the ready tag, then run preflight.")


if __name__ == "__main__":
    main()
