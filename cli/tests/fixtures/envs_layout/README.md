# envs_layout fixture

Stress-tests `cli/infracanvas/parser/module.py::resolve_modules` and `cli/infracanvas/parser/hcl.py::_extract_resources` end-to-end.

## Shape

```
envs_layout/
├── envs/prod/main.tf        # root module: provider + module "vpc" + module "broken" + data source
├── modules/vpc/main.tf      # local submodule: variable + count + aws_vpc + aws_subnet + output
└── modules/broken/main.tf   # deliberately malformed HCL — exercises D-01 parse-error surfacing
```

## What this fixture covers

- **Phase 5.1 D-01 (warn + continue):** `modules/broken/main.tf` contains invalid HCL. `resolve_modules` must merge the submodule's `parse_errors` into the caller's list and synthesize a placeholder node for the unresolvable module. Scan exit code stays 0.
- **Phase 5.1 D-02 (count expansion):** `modules/vpc/main.tf` has `resource "aws_subnet" "public" { count = var.az_count }`. Because `var.az_count` is non-literal, the parser keeps a single collapsed node with `unresolved_count=True`. If a future phase resolves `var.*` to the caller-passed literal `3`, expansion produces three instances: `module.vpc.aws_subnet.public[0..2]`.
- **Phase 5.1 D-04 (envs-layout):** realistic directory shape (`envs/prod` + `modules/vpc`) matches how Terraform code is laid out in production.

## Not covered (explicitly deferred — see CONTEXT.md `<deferred>`)

- Registry sources (`source = "terraform-aws-modules/vpc/aws"`) — v1.2.
- Full cross-module `var.*` / `local.*` / `data.*` resolution — future phase.
- `.tfvars` auto-discovery.
