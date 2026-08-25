load("@build_bazel_rules_swift//swift:swift.bzl", "swift_library")
load("@build_bazel_rules_apple//apple:resources.bzl", "apple_resource_bundle")
load("//build-system/bazel-utils:plist_fragment.bzl", "plist_fragment")

plist_fragment(
    name = "NagramiXLocalizationInfoPlist",
    extension = "plist",
    template =
    """
    <key>CFBundleIdentifier</key>
    <string>com.gamesfanteam.nagramix.localization</string>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleName</key>
    <string>NagramiXLocalization</string>
    """,
)

apple_resource_bundle(
    name = "NagramiXLocalization",
    infoplists = [
        ":NagramiXLocalizationInfoPlist",
    ],
    resources = glob([
        "Resources/**/*",
    ]),
)

swift_library(
    name = "NagramiXCore",
    module_name = "NagramiXCore",
    srcs = glob([
        "Sources/**/*.swift",
    ]),
    copts = [
        "-warnings-as-errors",
    ],
    data = [
        ":NagramiXLocalization",
    ],
    deps = [
        "//submodules/TelegramPresentationData:TelegramPresentationData",
    ],
    visibility = [
        "//visibility:public",
    ],
)
