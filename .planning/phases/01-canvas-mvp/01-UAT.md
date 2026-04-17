---
status: testing
phase: 01-canvas-mvp
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md, 01-05-SUMMARY.md, 01-06-SUMMARY.md, 01-07-SUMMARY.md]
started: 2026-04-17T00:00:00Z
updated: 2026-04-17T11:45:00Z
status: partial
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state. Start the application from scratch. CLI boots without errors, and a basic command (scan or score) completes successfully.
result: pass

### 2. Search Bar Appears and Filters Resources
expected: Open the HTML diagram viewer. A search box appears at the top of the canvas. Type a resource name or ID. Non-matching resources dim to 20% opacity. Clear the search box. All resources return to full opacity.
result: pass

### 3. Shadow Resources Display Dashed Borders
expected: Open the HTML diagram viewer for a Terraform directory containing shadow resources (resources in tfstate but not in HCL). Shadow resources show a dashed border and dimmed opacity (20%) compared to regular resources. Hovering over a shadow resource displays an orange "shadow" badge.
result: pending

### 4. Gate Overlay Blocks Findings Detail
expected: Open the HTML diagram viewer with gateMode enabled (checked via window.__INFRACANVAS_GATE__). Click a resource with security findings. The DetailPanel opens with a lock icon, finding count, severity summary, and "Unlock details" CTA linking to https://infracanvas.dev/founding. Raw findings are not visible.
result: pass

### 5. Scan Command Defaults to HTML Output
expected: Run `infracanvas scan <directory>` without specifying a format. The command produces an HTML file (infracanvas.html) instead of JSON. The HTML file can be opened in a browser.
result: pass

### 6. Browser Opens Automatically on Local Scan
expected: Run `infracanvas scan <directory>` on a local machine (not in CI). A browser window opens automatically displaying the diagram. In CI environment (GitHub Actions, CircleCI, Travis, Jenkins), browser does not open.
result: pending

### 7. Serve Command Watches for Changes
expected: Run `infracanvas serve <directory>` on a local directory. An HTTP server starts on port 8080. Open http://localhost:8080 in a browser. Modify a .tf file. The server detects the change and the browser automatically reloads the diagram (verify via browser console or visible update).
result: pending

### 8. Diagram Displays All 15 Resource Type Icons
expected: Open the HTML diagram viewer for a Terraform configuration containing AWS resources (EC2, S3, RDS, IAM, KMS, VPC, Subnet, Security Group, NAT Gateway, CloudWatch Log, ElastiCache, ECS, DynamoDB, Lambda, CloudFront). All resources render with distinct icons matching their type.
result: pending

### 9. Viewer HTML is Under 5MB
expected: Build the viewer with `npm run build` in the viewer directory. Check the size of dist/index.html. File size is under 5MB. The HTML file contains the __INFRACANVAS_DATA__ placeholder and no external <script src=> tags (fully inlined).
result: pass

### 10. Score Command Produces HTML with Letter Grade
expected: Run `infracanvas score <directory>`. Command prints a Rich terminal table showing the security score and dimension breakdown. A file infracanvas-score.html is created. The HTML displays a large letter grade (A/B/C/D/F) with "N / 100" score below.
result: pass

### 11. Score Card Shows 5 Dimension Progress Bars
expected: Open the infracanvas-score.html file in a browser. Verify the page displays 5 progress bars labeled: Security, Encryption, IAM Hygiene, Cost Efficiency, Tagging. Each bar is filled proportionally to the dimension score. Each bar has a distinct color (Security=#3b82f6, Encryption=#a855f7, IAM Hygiene=#f97316, Cost Efficiency=#22c55e, Tagging=#64748b).
result: pass

### 12. Score Card Upgrade CTA Links to Founding Page
expected: Open infracanvas-score.html. Locate the "Unlock details" or "Upgrade" call-to-action button. Click it. The browser navigates to https://infracanvas.dev/founding.
result: pass

### 13. Recursive Module Parsing Works
expected: Run `infracanvas scan <directory>` on a Terraform configuration using local modules (./modules/...). The CLI successfully parses the modules and includes all module resources in the diagram. No errors or infinite loops occur (circular module references are detected and skipped).
result: pending

### 14. Shadow Infrastructure Pipeline Works
expected: Ensure a .terraform/modules/.modules.json and terraform.tfstate file exist in the Terraform directory. Run `infracanvas scan <directory>`. Resources in tfstate but not in HCL appear in the diagram with `drift=shadow`. No resources are missed or duplicated.
result: pending

### 15. Resource Graph v2.0 Schema is Emitted
expected: Run `infracanvas scan <directory> --format json`. The output JSON file contains `"version": "2.0"` at the root. (Do not run with --format json; if you can visually inspect the HTML's embedded data, check the browser console for window.__INFRACANVAS_DATA__.version.)
result: pending

### 16. README Exists and is Installation-Ready
expected: Check the repository root. README.md exists and is under 250 lines. It describes the quick start (3 steps), installation methods (PyPI, Homebrew, source), and lists the 15 AWS resource types and 10 security rules. Verify you can follow the "Quick Start" section and install the CLI.
result: pending

### 17. License Exists
expected: Check the repository root. LICENSE file exists and contains MIT License text. File is named exactly "LICENSE" (not LICENSE.md or COPYING).
result: pending

### 18. GitHub Actions Release Workflow is Configured
expected: Check .github/workflows/cli-release.yml. The workflow contains: 'id-token: write' for OIDC, 'pypa/gh-action-pypi-publish' action, and a step that builds the viewer before publishing. Workflow triggers on version tag creation (e.g., v0.1.0).
result: pending

## Summary

total: 18
passed: 9
issues: 0
pending: 9
skipped: 0

## Gaps

[none yet]
