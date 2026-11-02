#pragma once
#ifdef __cplusplus
extern "C" {
#endif
// cancelled must be thread-safe and must not release opaque until return.
int nx_vosk_transcribe(const char *model_path, const float *samples, int count,
                      int (*cancelled)(void *), void *opaque, char **output);
void nx_vosk_free_text(char *output);
#ifdef __cplusplus
}
#endif
