load("@build_bazel_rules_swift//swift:swift.bzl", "swift_library")

# Foundation-only: the photo resource fetcher must not depend on UI modules.
swift_library(
    name = "NagramiXMediaSettings",
    module_name = "NagramiXMediaSettings",
    srcs = glob(["Sources/**/*.swift"]),
    copts = ["-warnings-as-errors"],
    visibility = ["//visibility:public"],
)
