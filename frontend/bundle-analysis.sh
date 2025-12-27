#!/bin/bash

echo "=== Bundle Size Analysis ==="
echo ""

# Calculate total gzip size
total_gzip=0
total_unminified=0

echo "Asset Breakdown (Top 20 largest):"
echo "=================================="
du -sh dist/assets/*.js dist/assets/*.css 2>/dev/null | sort -hr | head -20

echo ""
echo "Bundle Statistics:"
echo "=================="

# Get actual gzip sizes from build output
echo "Total build output from Vite:"
ls -lah dist/ | grep -E "^-" | awk '{print $5, $9}'

# Calculate total size
echo ""
echo "Checking dist directory size..."
du -sh dist/

