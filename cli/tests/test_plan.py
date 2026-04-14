"""Tests for the Terraform plan reader (T-015)."""

from pathlib import Path

from infracanvas.graph.models import DriftStatus
from infracanvas.parser.plan import PlanReader

FIXTURES = Path(__file__).parent / "fixtures"


class TestPlanReader:
    def setup_method(self):
        self.reader = PlanReader()
        self.changes = self.reader.read(FIXTURES / "sample_plan.json")

    def test_parse_create(self):
        nat = next(c for c in self.changes if c.resource_address == "aws_nat_gateway.main")
        assert nat.action == DriftStatus.added
        assert nat.after.get("subnet_id") == "subnet-abc123"

    def test_parse_update(self):
        instance = next(c for c in self.changes if c.resource_address == "aws_instance.app")
        assert instance.action == DriftStatus.changed
        type_change = next(a for a in instance.attribute_changes if a.attribute == "instance_type")
        assert type_change.before == "t3.medium"
        assert type_change.after == "m5.large"

    def test_parse_delete(self):
        bucket = next(c for c in self.changes if c.resource_address == "aws_s3_bucket.old")
        assert bucket.action == DriftStatus.deleted
        assert bucket.before.get("bucket") == "my-old-bucket"

    def test_parse_noop(self):
        vpc = next(c for c in self.changes if c.resource_address == "aws_vpc.main")
        assert vpc.action == DriftStatus.unchanged
        assert len(vpc.attribute_changes) == 0

    def test_replace_maps_to_changed(self):
        lam = next(c for c in self.changes if c.resource_address == "aws_lambda_function.replace_me")
        assert lam.action == DriftStatus.changed
        runtime_change = next(a for a in lam.attribute_changes if a.attribute == "runtime")
        assert runtime_change.before == "python3.9"
        assert runtime_change.after == "python3.12"

    def test_sensitive_attrs_redacted(self):
        db = next(c for c in self.changes if c.resource_address == "aws_db_instance.secrets")
        pw_change = next(a for a in db.attribute_changes if a.attribute == "password")
        assert pw_change.sensitive is True
        assert pw_change.before == "[sensitive]"
        assert pw_change.after == "[sensitive]"

    def test_empty_plan_no_error(self):
        changes = self.reader.parse({"resource_changes": []})
        assert changes == []

    def test_unknown_action_defaults_unchanged(self):
        changes = self.reader.parse({
            "resource_changes": [{
                "address": "aws_foo.bar",
                "type": "aws_foo",
                "name": "bar",
                "change": {
                    "actions": ["import"],
                    "before": {},
                    "after": {},
                    "before_sensitive": {},
                    "after_sensitive": {},
                },
            }]
        })
        assert len(changes) == 1
        assert changes[0].action == DriftStatus.unchanged
