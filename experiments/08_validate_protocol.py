from unapproved_sum.authority_corpus import load_records, load_sources, validate_corpus
from unapproved_sum.policy_box import load_policy_box, validate_policy_box
from unapproved_sum.protocol import expected_trajectory_count, openai_replication_count, validate_protocol


def main() -> None:
    errors = list(validate_protocol())
    errors.extend(validate_corpus(load_records(), load_sources()))
    errors.extend(validate_policy_box(load_policy_box()))
    if errors:
        print("PROTOCOL VALIDATION: FAIL")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("PROTOCOL VALIDATION: PASS")
    print("OpenAI replication trajectories:", openai_replication_count())
    print("Total cross-provider trajectories:", expected_trajectory_count())


if __name__ == "__main__":
    main()
