#!/bin/bash

set -e

WORKFLOW_FILE="publish.yml"

# 1. Get version from argument or prompt
if [ -z "$1" ]; then
  read -p "Enter new version (e.g., 1.2.3): " VERSION
else
  VERSION="$1"
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must be semantic (x.y.z). Got: $VERSION" >&2
  exit 1
fi

if ! command -v gh &> /dev/null; then
  echo "GitHub CLI (gh) is required for release dispatch." >&2
  echo "Install gh and authenticate, then run this script again." >&2
  exit 1
fi

echo "Dispatching one-click release workflow ($WORKFLOW_FILE) with version $VERSION..."
gh workflow run "$WORKFLOW_FILE" --field version="$VERSION"

echo "Release workflow dispatched."
echo "Track progress in GitHub Actions: publish workflow -> release PR -> auto-merge -> tag -> release publish."

echo "Done!"