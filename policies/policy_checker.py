
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

POLICY_FILE = PROJECT_ROOT / "policies" / "cost-policy.json"
TERRAFORM_FILE = PROJECT_ROOT / "examples" / "ec2-cost-example.tf"
INFRACOST_REPORT_FILE = PROJECT_ROOT / "infracost-report.json"


def load_policy():
    with POLICY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_terraform_config():
    with TERRAFORM_FILE.open("r", encoding="utf-8") as file:
        terraform = file.read()

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
        raise ValueError(
            "Could not read environment or instance_type from Terraform."
        )

    return terraform, environment_match.group(1), instance_match.group(1)


def check_terraform(policy, terraform, environment, instance_type):
    errors = []
    warnings = []

    allowed_type = policy["max_instance_types"].get(environment)

    if allowed_type is None:
        errors.append(
            f"No instance-type policy defined for environment '{environment}'."
        )
    elif instance_type != allowed_type:
        errors.append(
            f"Environment '{environment}' requires {allowed_type}, "
            f"but Terraform specifies {instance_type}."
        )

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
            if not re.search(
                rf'^\s*{re.escape(tag)}\s*=',
                tags_block,
                re.MULTILINE,
            ):
                errors.append(f"Required tag '{tag}' is missing.")

    return errors, warnings


def check_cost(policy, environment):
    errors = []
    warnings = []

    try:
        with INFRACOST_REPORT_FILE.open(
            "r", encoding="utf-8-sig"
        ) as file:
            report = json.load(file)

        monthly_cost = float(report["summary"]["total_monthly_cost"])
        budget = float(policy["environment_budgets"][environment])

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"Could not read or validate cost report/policy: {exc}")
        return errors, warnings

    print(f"Environment: {environment}")
    print(f"Estimated monthly cost: ${monthly_cost:.2f}")
    print(f"Environment budget: ${budget:.2f}")

    if monthly_cost > budget:
        errors.append(
            f"Estimated monthly cost ${monthly_cost:.2f} exceeds "
            f"the {environment} budget of ${budget:.2f}."
        )

    return errors, warnings


def main():
    policy = load_policy()

    try:
        terraform, environment, instance_type = get_terraform_config()
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)

    terraform_errors, terraform_warnings = check_terraform(
        policy, terraform, environment, instance_type
    )

    cost_errors, cost_warnings = check_cost(policy, environment)

    errors = terraform_errors + cost_errors
    warnings = terraform_warnings + cost_warnings

    print("\nCostSentinel Policy Check")
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