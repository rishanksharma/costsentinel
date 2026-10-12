
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

POLICY_FILE = PROJECT_ROOT / "policies" / "cost-policy.json"
TERRAFORM_FILE = PROJECT_ROOT / "examples" / "ec2-cost-example.tf"


def load_policy():
    with POLICY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def check_terraform(policy):
    with TERRAFORM_FILE.open("r", encoding="utf-8") as file:
        terraform = file.read()

    errors = []
    warnings = []

    # Read the configured environment and instance type.
    environment_match = re.search(
        r'variable\s+"environment".*?default\s*=\s*"([^"]+)"',
        terraform,
        re.DOTALL,
    )
    instance_match = re.search(
        r'variable\s+"instance_type".*?default\s*=\s*"([^"]+)"',
        terraform,
        re.DOTALL,
    )

    if not environment_match or not instance_match:
        errors.append("Could not read environment or instance_type from Terraform.")
        return errors, warnings

    environment = environment_match.group(1)
    instance_type = instance_match.group(1)

    # Check whether the instance type matches the environment policy.
    allowed_type = policy["max_instance_types"].get(environment)

    if allowed_type is None:
        errors.append(f"No instance-type policy defined for environment '{environment}'.")
    elif instance_type != allowed_type:
        errors.append(
            f"Environment '{environment}' requires {allowed_type}, "
            f"but Terraform specifies {instance_type}."
        )

    # Check required tags in the resource's tags block.
    tags_match = re.search(
        r'resource\s+"aws_instance"\s+"[^"]+".*?tags\s*=\s*\{(.*?)\}',
        terraform,
        re.DOTALL,
    )

    if not tags_match:
        errors.append("Could not find a tags block in the EC2 resource.")
    else:
        tags_block = tags_match.group(1)

        for tag in policy["require_tags"]:
            if not re.search(rf'^\s*{re.escape(tag)}\s*=', tags_block, re.MULTILINE):
                errors.append(f"Required tag '{tag}' is missing.")

    return errors, warnings


def main():
    policy = load_policy()
    errors, warnings = check_terraform(policy)

    print("CostSentinel Policy Check")
    print("-" * 30)

    for warning in warnings:
        print(f"WARN: {warning}")

    for error in errors:
        print(f"FAIL: {error}")

    if errors:
        print("\nResult: FAIL")
        raise SystemExit(1)

    print("\nResult: PASS")


if __name__ == "__main__":
    main()
