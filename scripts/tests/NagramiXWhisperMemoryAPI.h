#pragma once
// Deliberate C API boundary for portable CI; the production bridge is also
// compiled against pinned real whisper.cpp headers in the recorded native probe.
enum ggml_log_level { GGML_LOG_LEVEL_INFO };
using ggml_log_callback = void (*)(ggml_log_level,const char*,void*);
struct whisper_context;
struct whisper_context_params {bool use_gpu;bool flash_attn;};
enum whisper_sampling_strategy {WHISPER_SAMPLING_GREEDY};
struct whisper_full_params {
 whisper_sampling_strategy strategy;
 int n_threads;
 const char *language;
 bool translate,no_context,print_special,print_progress,print_realtime,print_timestamps;
 float temperature,temperature_inc;
 struct {int best_of;} greedy;
 bool suppress_blank;
 bool (*abort_callback)(void*);
 void *abort_callback_user_data;
};
void whisper_log_set(ggml_log_callback,void*);
whisper_context_params whisper_context_default_params();
whisper_context*whisper_init_from_file_with_params(const char*,whisper_context_params);
void whisper_free(whisper_context*);
whisper_full_params whisper_full_default_params(whisper_sampling_strategy);
int whisper_full(whisper_context*,whisper_full_params,const float*,int);
int whisper_full_n_segments(whisper_context*);
float whisper_full_get_segment_no_speech_prob(whisper_context*,int);
const char*whisper_full_get_segment_text(whisper_context*,int);
