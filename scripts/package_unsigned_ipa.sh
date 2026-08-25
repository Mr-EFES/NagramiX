#!/bin/bash
set -euo pipefail

APP_PATH="${1:?usage: package_unsigned_ipa.sh path/to/App.app output.ipa bundle.id version}"
OUTPUT_PATH="${2:?usage: package_unsigned_ipa.sh path/to/App.app output.ipa bundle.id version}"
TARGET_BUNDLE_ID="${3:?usage: package_unsigned_ipa.sh path/to/App.app output.ipa bundle.id version}"
TARGET_VERSION="${4:?usage: package_unsigned_ipa.sh path/to/App.app output.ipa bundle.id version}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Application bundle not found: $APP_PATH" >&2
  exit 1
fi

rm -rf .nagramix-package
rm -f "$OUTPUT_PATH"
mkdir -p .nagramix-package/Payload
cp -R "$APP_PATH" .nagramix-package/Payload/NagramiX.app
find .nagramix-package/Payload/NagramiX.app -name '_CodeSignature' -type d -prune -exec rm -rf {} +
find .nagramix-package/Payload/NagramiX.app -name 'embedded.mobileprovision' -type f -delete

# The upstream target keeps "Telegram" as the root Info.plist display name even
# when the Bazel product is renamed. This metadata-only rewrite is safe after
# stripping the temporary build signature; the bundle identifier itself must
# already have been compiled with the NagramiX configuration.
/usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName NagramiX' .nagramix-package/Payload/NagramiX.app/Info.plist
/usr/libexec/PlistBuddy -c 'Set :CFBundleName NagramiX' .nagramix-package/Payload/NagramiX.app/Info.plist
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $TARGET_VERSION" .nagramix-package/Payload/NagramiX.app/Info.plist

final_id="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' .nagramix-package/Payload/NagramiX.app/Info.plist)"
test "$final_id" = "$TARGET_BUNDLE_ID" || { echo "Unexpected final bundle id: $final_id" >&2; exit 1; }
final_name="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' .nagramix-package/Payload/NagramiX.app/Info.plist)"
test "$final_name" = "NagramiX" || { echo "Unexpected final display name: $final_name" >&2; exit 1; }
final_version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' .nagramix-package/Payload/NagramiX.app/Info.plist)"
test "$final_version" = "$TARGET_VERSION" || { echo "Unexpected final version: $final_version" >&2; exit 1; }
(
  cd .nagramix-package
  /usr/bin/zip -qry "../$OUTPUT_PATH" Payload
)
echo "Created unsigned IPA: $OUTPUT_PATH ($final_id, version $final_version)"
