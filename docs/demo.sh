#!/bin/bash
# Script for recording terminal demo — run with: asciinema rec demo.cast
sleep 1
echo "$ infracanvas scan ./terraform"
sleep 0.5
infracanvas scan ./tests/fixtures/demo_infra --format json | head -5
sleep 1
echo ""
echo "$ infracanvas score ./terraform"
sleep 0.5
infracanvas score ./tests/fixtures/demo_infra
