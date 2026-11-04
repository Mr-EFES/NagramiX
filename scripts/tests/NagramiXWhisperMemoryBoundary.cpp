#include "Bridge.h"
#include "whisper.h"
#include <cassert>
#include <cmath>
#include <new>
#include <string>
#include <iostream>
struct whisper_context {};
static bool use_gpu=true,flash=false;
static int best_of=0,freed=0,mode=0;
void whisper_log_set(ggml_log_callback,void*){}
whisper_context_params whisper_context_default_params(){whisper_context_params p{};p.use_gpu=true;return p;}
whisper_context*whisper_init_from_file_with_params(const char*,whisper_context_params p){use_gpu=p.use_gpu;flash=p.flash_attn;if(mode==1)throw std::bad_alloc();return new whisper_context;}
void whisper_free(whisper_context*p){freed++;delete p;}
whisper_full_params whisper_full_default_params(whisper_sampling_strategy s){whisper_full_params p{};p.strategy=s;p.greedy.best_of=5;return p;}
int whisper_full(whisper_context*,whisper_full_params p,const float*,int){best_of=p.greedy.best_of;if(mode==2)throw std::bad_alloc();return 0;}
int whisper_full_n_segments(whisper_context*){return 1;}
float whisper_full_get_segment_no_speech_prob(whisper_context*,int){return 0;}
const char*whisper_full_get_segment_text(whisper_context*,int){return "hello";}
int main(){
 float pcm[160]={0.5f};char*text=nullptr;auto*session=nx_whisper_create();
 assert(nx_whisper_transcribe(session,"model",pcm,160,"ru",2,&text)==0);
 assert(!use_gpu&&flash&&best_of==1&&text&&std::string(text)=="hello"&&freed==1);nx_whisper_free_text(text);
 mode=1;text=nullptr;assert(nx_whisper_transcribe(session,"model",pcm,160,"ru",2,&text)==4&&text==nullptr&&freed==1);
 mode=2;assert(nx_whisper_transcribe(session,"model",pcm,160,"ru",2,&text)==4&&text==nullptr&&freed==2);
 mode=0;nx_whisper_cancel(session);assert(nx_whisper_transcribe(session,"model",pcm,160,"ru",2,&text)==1);nx_whisper_destroy(session);
 session=nx_whisper_create();float bad[1]={NAN};assert(nx_whisper_transcribe(session,"model",bad,1,"ru",2,&text)==2);float silence[1]={0};assert(nx_whisper_transcribe(session,"model",silence,1,"ru",2,&text)==3);nx_whisper_destroy(session);
 std::cout<<"PASS: actual Whisper bridge CPU/flash/one-decoder policy, allocation failure cleanup, cancellation, NaN and silence; C API is a boundary\n";
}
