#include "Bridge.h"
#include "vosk_api.h"
#include <cassert>
#include <cstring>
#include <string>
struct VoskModel {};
struct VoskRecognizer { int calls=0; };
extern "C" {
void vosk_set_log_level(int) {}
VoskModel* vosk_model_new(const char*) { return new VoskModel; }
void vosk_model_free(VoskModel* m) { delete m; }
VoskRecognizer* vosk_recognizer_new(VoskModel*, float rate) { assert(rate==16000); return new VoskRecognizer; }
void vosk_recognizer_free(VoskRecognizer* r) { delete r; }
int vosk_recognizer_accept_waveform_f(VoskRecognizer* r,const float* samples,int count) { assert(count>0 && count<=4000); assert(samples[0]>32000);return ++r->calls==1 ? 1 : 0; }
const char* vosk_recognizer_result(VoskRecognizer*) { return "{\"text\":\"first\"}"; }
const char* vosk_recognizer_final_result(VoskRecognizer*) { return "{\"text\":\"last\"}"; }
}
int never(void*) { return 0; }
int always(void*) { return 1; }
int main() {
 float samples[8001];for(float &x:samples)x=1;
 char* out=nullptr;
 assert(nx_vosk_transcribe("model",samples,8001,never,nullptr,&out)==0);
 assert(out && std::string(out)=="[{\"text\":\"first\"},{\"text\":\"last\"}]");nx_vosk_free_text(out);
 out=nullptr;
 assert(nx_vosk_transcribe("model",samples,8001,always,nullptr,&out)==1 && !out);
 assert(nx_vosk_transcribe("model",nullptr,8001,never,nullptr,&out)==2 && !out);
}
