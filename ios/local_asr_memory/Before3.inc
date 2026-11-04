#include <algorithm>
#include "Bridge.h"
#include "whisper.h"
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <mutex>
#include <string>
#include <memory>

struct NXWhisperSession { std::atomic<bool> cancelled{false}; };
static void silent_log(enum ggml_log_level, const char *, void *) {}
NXWhisperSession * nx_whisper_create(void) { return new NXWhisperSession(); }
void nx_whisper_cancel(NXWhisperSession * session) { if (session) session->cancelled.store(true); }
void nx_whisper_destroy(NXWhisperSession * session) { delete session; }
void nx_whisper_free_text(char * text) { std::free(text); }
int nx_whisper_transcribe(NXWhisperSession * session, const char * model_path,
                         const float * samples, int count, const char * language,
                         int threads, char ** output) {
    if (!session || !model_path || !samples || !language || !output || count <= 0 || count > 16000 * 900) return 2;
    *output = nullptr;
    if (session->cancelled.load()) return 1;
    float peak = 0.0f;
    for (int i = 0; i < count; ++i) {
        if (!std::isfinite(samples[i])) return 2;
        peak = std::max(peak, std::abs(samples[i]));
    }
    if (peak < 0.0001f) return 3;
    static std::once_flag logging;
    std::call_once(logging, [] { whisper_log_set(silent_log, nullptr); });
    auto cp = whisper_context_default_params(); cp.use_gpu = false;
    std::unique_ptr<whisper_context, decltype(&whisper_free)> context(whisper_init_from_file_with_params(model_path, cp), whisper_free);
    if (!context) return 2;
    if (session->cancelled.load()) return 1;
    auto params = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    params.n_threads = std::max(1, std::min(threads, 4));
    params.language = language;
    params.translate = false; params.no_context = true;
    params.print_special = false; params.print_progress = false;
    params.print_realtime = false; params.print_timestamps = false;
    params.temperature = 0.0f; params.temperature_inc = 0.0f;
    params.suppress_blank = true;
    params.abort_callback = [](void * opaque) { return static_cast<NXWhisperSession *>(opaque)->cancelled.load(); };
    params.abort_callback_user_data = session;
    const int result = whisper_full(context.get(), params, samples, count);
    if (session->cancelled.load()) return 1;
    if (result != 0) return 2;
    std::string text;
    for (int i = 0; i < whisper_full_n_segments(context.get()); ++i) {
        if (whisper_full_get_segment_no_speech_prob(context.get(), i) >= 0.8f) continue;
        const char * segment = whisper_full_get_segment_text(context.get(), i);
        if (segment) text += segment;
    }
    if (text.empty()) return 3;
    *output = static_cast<char *>(std::malloc(text.size() + 1));
    if (!*output) return 2;
    std::memcpy(*output, text.c_str(), text.size() + 1);
    return 0;
}
