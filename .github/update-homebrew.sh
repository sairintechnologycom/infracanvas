#!/usr/bin/env bash
# Usage: ./update-homebrew.sh <version> <sha256>
# Updates Formula/infracanvas.rb with new version and SHA256 at release time.
VERSION="$1"
SHA256="$2"

if [[ -z "$VERSION" || -z "$SHA256" ]]; then
  echo "Usage: $0 <version> <sha256>"
  exit 1
fi

sed -i "s/VERSION/$VERSION/g" Formula/infracanvas.rb
sed -i "s/SHA256_PLACEHOLDER/$SHA256/g" Formula/infracanvas.rb
echo "Updated Formula/infracanvas.rb to version $VERSION"
