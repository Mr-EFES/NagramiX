load("@rules_cc//cc:cc_library.bzl", "cc_library")

# whisper.cpp v1.7.6, a8d002cfd879315632a579e73f0148d06959de36.
# CPU + Accelerate: no runtime shader compilation, GPU context or second player.
cc_library(
    name = "whisper",
    srcs = [
        "src/whisper.cpp",
        "ggml/src/ggml.c", "ggml/src/ggml.cpp", "ggml/src/ggml-alloc.c",
        "ggml/src/ggml-backend.cpp", "ggml/src/ggml-backend-reg.cpp",
        "ggml/src/ggml-opt.cpp", "ggml/src/ggml-threading.cpp",
        "ggml/src/ggml-quants.c", "ggml/src/gguf.cpp",
        "ggml/src/ggml-cpu/ggml-cpu.c", "ggml/src/ggml-cpu/ggml-cpu.cpp",
        "ggml/src/ggml-cpu/repack.cpp", "ggml/src/ggml-cpu/hbm.cpp",
        "ggml/src/ggml-cpu/quants.c", "ggml/src/ggml-cpu/traits.cpp",
        "ggml/src/ggml-cpu/binary-ops.cpp", "ggml/src/ggml-cpu/unary-ops.cpp",
        "ggml/src/ggml-cpu/vec.cpp", "ggml/src/ggml-cpu/ops.cpp",
        "ggml/src/ggml-cpu/amx/amx.cpp", "ggml/src/ggml-cpu/amx/mmq.cpp",
    ] + select({
        "@platforms//cpu:aarch64": ["ggml/src/ggml-cpu/arch/arm/quants.c", "ggml/src/ggml-cpu/arch/arm/repack.cpp"],
        "@platforms//cpu:x86_64": ["ggml/src/ggml-cpu/arch/x86/quants.c", "ggml/src/ggml-cpu/arch/x86/repack.cpp"],
        "//conditions:default": [],
    }),
    hdrs = glob(["include/*.h", "src/*.h", "ggml/include/*.h", "ggml/src/**/*.h"]),
    includes = ["include", "src", "ggml/include", "ggml/src", "ggml/src/ggml-cpu"],
    defines = ["GGML_USE_CPU", "GGML_VERSION=\"0.0.0\"", "GGML_COMMIT=\"a8d002c\""] + select({
        "@platforms//os:ios": ["GGML_USE_ACCELERATE"],
        "@platforms//os:macos": ["GGML_USE_ACCELERATE"],
        "//conditions:default": ["_GNU_SOURCE"],
    }),
    copts = ["-O2"],
    cxxopts = ["-std=c++17"],
    linkopts = select({
        "@platforms//os:ios": ["-framework", "Accelerate"],
        "@platforms//os:macos": ["-framework", "Accelerate"],
        "//conditions:default": ["-pthread", "-ldl"],
    }),
    visibility = ["//visibility:public"],
)
