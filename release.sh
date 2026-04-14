#!/bin/bash

set -e

MANIFEST="custom_components/sh_entity_status/manifest.json"

# 1. Get version from argument or prompt
if [ -z "$1" ]; then
  read -p "Enter new version (e.g., 1.2.3): " VERSION
else
  VERSION="$1"
fi

# 2. Update manifest.json
echo "Updating manifest.json to version $VERSION..."
jq --arg v "$VERSION" '.version = $v' "$MANIFEST" > "$MANIFEST.tmp" && mv "$MANIFEST.tmp" "$MANIFEST"

# 3. Commit the change
git add "$MANIFEST"
git commit -m "Bump version to $VERSION"

# 4. Tag and push
git tag "v$VERSION"
git push
git push --tags

# 5. (Optional) Create GitHub release (requires gh CLI)
if command -v gh &> /dev/null; then
  gh release create "v$VERSION" --title "v$VERSION" --notes "Release v$VERSION"
fi

echo "Done! Version $VERSION released and manifest updated."