load("@rules_cc//cc:objc_library.bzl", "objc_library")

exports_files(["upstream.BUILD"])
objc_library(
    name = "NagramiXWhisper",
    module_name = "NagramiXWhisper",
    enable_modules = True,
    srcs = ["Bridge.cpp"],
    hdrs = ["Bridge.h"],
    copts = ["-std=c++17", "-O2"],
    deps = ["@nagramix_whisper//:whisper"],
    visibility = ["//visibility:public"],
)
