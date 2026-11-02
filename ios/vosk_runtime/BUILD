load("@rules_cc//cc:objc_library.bzl", "objc_library")
exports_files(["upstream.BUILD"])
objc_library(
    name = "NagramiXVosk",
    module_name = "NagramiXVosk",
    enable_modules = True,
    srcs = ["Bridge.cpp"],
    hdrs = ["Bridge.h", "vosk_api.h"],
    copts = ["-std=c++17", "-O2"],
    sdk_frameworks = ["Accelerate"],
    sdk_dylibs = ["c++", "z"],
    deps = ["@nagramix_vosk//:vosk"],
    visibility = ["//visibility:public"],
)
