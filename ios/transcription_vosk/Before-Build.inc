load("@build_bazel_rules_swift//swift:swift.bzl", "swift_library")

swift_library(
    name = "NagramiXTranscription",
    module_name = "NagramiXTranscription",
    srcs = glob(["Sources/**/*.swift"]),
    copts = ["-warnings-as-errors"],
    deps = [
        "//submodules/SSignalKit/SwiftSignalKit",
        "//submodules/Display", "//submodules/AsyncDisplayKit",
        "//submodules/TelegramPresentationData", "//submodules/ItemListUI",
        "//submodules/AccountContext", "//submodules/TelegramCore",
        "//submodules/MediaPlayer:UniversalMediaPlayer",
        "//submodules/NagramiXTranscription/Whisper:NagramiXWhisper",
    ],
    visibility = ["//visibility:public"],
)
