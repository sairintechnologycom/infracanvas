"""Detect implicit resource references in Terraform attribute values."""

from __future__ import annotations

import re

# Matches patterns like: aws_vpc.main.id, aws_subnet.public[0].id, module.networking.vpc_id
RESOURCE_REF_PATTERN = re.compile(
    r"\b([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)\b"
)

# Known Terraform resource type prefixes (the 15 supported AWS types)
SUPPORTED_RESOURCE_TYPES: set[str] = {
    "aws_vpc",
    "aws_subnet",
    "aws_security_group",
    "aws_instance",
    "aws_s3_bucket",
    "aws_rds_instance",
    "aws_db_instance",
    "aws_iam_role",
    "aws_iam_policy",
    "aws_lambda_function",
    "aws_alb",
    "aws_lb",
    "aws_cloudfront_distribution",
    "aws_kms_key",
    "aws_dynamodb_table",
}


def find_references(value: object, known_resources: set[str]) -> set[str]:
    """Recursively search a value for references to known resources.

    Returns a set of resource IDs like {"aws_vpc.main", "aws_subnet.public"}.
    """
    refs: set[str] = set()
    _walk(value, known_resources, refs)
    return refs


def _walk(value: object, known_resources: set[str], refs: set[str]) -> None:
    if isinstance(value, str):
        for match in RESOURCE_REF_PATTERN.finditer(value):
            candidate = match.group(1)
            if candidate in known_resources:
                refs.add(candidate)
    elif isinstance(value, dict):
        for v in value.values():
            _walk(v, known_resources, refs)
    elif isinstance(value, list):
        for item in value:
            _walk(item, known_resources, refs)
