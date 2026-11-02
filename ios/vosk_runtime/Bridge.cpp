#include "Bridge.h"
#include "vosk_api.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <new>
#include <string>

void nx_vosk_free_text(char *output) { std::free(output); }
int nx_vosk_transcribe(const char *path, const float *samples, int count,
                      int (*cancelled)(void *), void *opaque, char **output) {
    if (!output) return 2;
    *output = nullptr;
    if (!path || !samples || !cancelled || count <= 0 || count > 16000 * 900) return 2;
    try {
        if (cancelled(opaque)) return 1;
        for (int i = 0; i < count; ++i) if (!std::isfinite(samples[i])) return 2;
        static std::once_flag logging;
        std::call_once(logging, [] { vosk_set_log_level(-1); });
        std::unique_ptr<VoskModel, decltype(&vosk_model_free)> model(vosk_model_new(path), vosk_model_free);
        if (!model) return 2;
        if (cancelled(opaque)) return 1;
        std::unique_ptr<VoskRecognizer, decltype(&vosk_recognizer_free)> recognizer(vosk_recognizer_new(model.get(), 16000.0f), vosk_recognizer_free);
        if (!recognizer) return 2;
        // Keep utterance endpointing from dropping earlier words. The caller
        // receives the concatenated JSON records, including the final record.
        std::string records = "[";
        bool first = true;
        auto append = [&](const char *record) {
            if (!record) return false;
            if (!first) records += ",";
            records += record;
            first = false;
            return records.size() <= 2000000;
        };
        for (int offset = 0; offset < count; offset += 4000) {
            if (cancelled(opaque)) return 1;
            const int length = std::min(4000, count - offset);
            float pcm[4000];
            for (int i = 0; i < length; ++i) pcm[i] = std::max(-1.0f, std::min(1.0f, samples[offset + i])) * 32767.0f;
            const int result = vosk_recognizer_accept_waveform_f(recognizer.get(), pcm, length);
            if (result < 0) return 2;
            if (result > 0 && !append(vosk_recognizer_result(recognizer.get()))) return 2;
        }
        if (cancelled(opaque)) return 1;
        if (!append(vosk_recognizer_final_result(recognizer.get()))) return 2;
        records += "]";
        *output = static_cast<char *>(std::malloc(records.size() + 1));
        if (!*output) return 2;
        std::memcpy(*output, records.c_str(), records.size() + 1);
        return 0;
    } catch (const std::bad_alloc &) { return 4; }
      catch (...) { return 2; }
}
