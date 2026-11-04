#ifndef NAGRAMIX_WHISPER_BRIDGE_H
#define NAGRAMIX_WHISPER_BRIDGE_H
#ifdef __cplusplus
extern "C" {
#endif
typedef struct NXWhisperSession NXWhisperSession;
NXWhisperSession * nx_whisper_create(void);
void nx_whisper_cancel(NXWhisperSession * session);
void nx_whisper_destroy(NXWhisperSession * session);
// 0 success, 1 cancelled, 2 invalid/model/decode error, 3 no speech, 4 allocation failure.
int nx_whisper_transcribe(NXWhisperSession * session, const char * model_path,
                         const float * samples, int count, const char * language,
                         int threads, char ** output);
void nx_whisper_free_text(char * text);
#ifdef __cplusplus
}
#endif
#endif
