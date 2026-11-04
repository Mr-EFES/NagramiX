@main enum Tests {
    static var count=0
    static func check(_ value:Bool,_ label:String){count+=1;if !value{fatalError("local ASR memory regression: "+label)}}
    static func failure(_ expected:NagramiXTranscriptionFailure,_ label:String,_ work:()throws->Void){do{try work();check(false,label)}catch{check(error as? NagramiXTranscriptionFailure==expected,label)}}
    static func integer(_ value:UInt64,_ width:Int)->Data{Data((0..<width).map{UInt8(truncatingIfNeeded:value >> (8*$0))})}
    static func fst(_ type:String,states:UInt64,arcs:UInt64)->Data {
        var value=integer(2125659606,4)
        for string in [type,"standard"]{value+=integer(UInt64(string.utf8.count),4);value+=Data(string.utf8)}
        value+=integer(2,4)+integer(0,4)+integer(0,8)+integer(0,8)+integer(states,8)+integer(arcs,8)
        return value
    }
    static func result(_ provider:NagramiXTranscriptionProvider,_ media:NagramiXTranscriptionMedia,_ config:NagramiXTranscriptionConfiguration,token:NagramiXTranscriptionCancellation=NagramiXTranscriptionCancellation())->Result<String,NagramiXTranscriptionFailure>{
        let done=DispatchSemaphore(value:0);var value:Result<String,NagramiXTranscriptionFailure>?
        let finish:(Result<String,NagramiXTranscriptionFailure>)->Void={value=$0;done.signal()}
        if provider == .whisper{NagramiXTranscriptionWhisper.transcribe(media:media,configuration:config,cancellation:token,completion:finish)}
        else{NagramiXTranscriptionVosk.transcribe(media:media,configuration:config,cancellation:token,completion:finish)}
        check(done.wait(timeout:.now()+5) == .success,"recognizer completes exactly through its worker")
        return value!
    }
    static func main()throws{
        let base=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:base,withIntermediateDirectories:true);defer{try? FileManager.default.removeItem(at:base)}
        let mib:UInt64=1024*1024
        check(NagramiXLocalInferenceMemory.whisperModels==[.base,.small_full,.large_v3_turbo_q8_0],"three user-requested tiers keep the proven Small and add mobile Turbo Q8")
        check(NagramiXTranscriptionConfiguration().whisper == .base,"new-install default uses the balanced mobile model")
        var legacy=NagramiXTranscriptionConfiguration();legacy.whisper = .large_v3
        check(try JSONDecoder().decode(NagramiXTranscriptionConfiguration.self,from:JSONEncoder().encode(legacy)).whisper == .large_v3,"existing Codable selection remains explicit and is never silently replaced")
        for language in NagramiXLocalInferenceMemory.voskLanguages {
            let mobile=NagramiXLocalInferenceMemory.voskModels(language:language)
            check(!mobile.isEmpty && mobile.count<=2 && mobile.allSatisfy{NagramiXLocalInferenceMemory.isMobileVosk($0)},"Vosk menu contains compact models and the explicitly verified Russian graph variant")
        }
        check(NagramiXLocalInferenceMemory.voskModels(language:"ru").map(\.name)==["vosk-model-small-ru-0.22","vosk-model-ru-0.10-lgraph"],"two real Russian download variants retain compact as first choice")
        check(!NagramiXLocalInferenceMemory.voskModels(language:"ru").contains{$0.name=="vosk-model-ru-0.42"},"multi-GB server model is excluded from new downloads")
        for model in NagramiXWhisperModel.allCases {
            let needed=try NagramiXLocalInferenceMemory.whisper(model)
            check(needed>UInt64(model.size),"all legacy Whisper variants retain workspace and reserve")
            try NagramiXLocalInferenceMemory.require(needed,available:needed)
            failure(.insufficientMemory,"one byte below budget refuses safely"){try NagramiXLocalInferenceMemory.require(needed,available:needed-1)}
        }
        for model:NagramiXWhisperModel in [.medium,.large_v3] {
            let needed=try NagramiXLocalInferenceMemory.whisper(model)
            check(needed<UInt64(model.size)*2+512*mib,"selected full model no longer needs two copies of its weights")
            try NagramiXLocalInferenceMemory.require(needed,available:5*1024*mib)
        }
        failure(.insufficientMemory,"full Large cannot fit into the total 3GB RAM of iPhone X"){try NagramiXLocalInferenceMemory.require(NagramiXLocalInferenceMemory.whisper(.large_v3),available:3*1024*mib)}
        failure(.tooLarge,"budget arithmetic cannot wrap"){_ = try NagramiXLocalInferenceMemory.sum(.max,1)}
        failure(.tooLarge,"multiplication cannot wrap"){_ = try NagramiXLocalInferenceMemory.product(.max,4)}
        let const=fst("const",states:10,arcs:30),vector=fst("vector",states:10,arcs:30)
        check(try NagramiXLocalInferenceMemory.fst(header:const,fileBytes:1000)==16*mib+10*32+30*16,"ConstFst uses state and arc layout")
        check(try NagramiXLocalInferenceMemory.fst(header:vector,fileBytes:1000)==16*mib+10*64+30*32,"VectorFst accounts for vector growth")
        check(try NagramiXLocalInferenceMemory.fst(header:Data([1]),fileBytes:1000)==2000,"unknown/truncated FST retains conservative fallback")
        for length in 0..<const.count{_ = try NagramiXLocalInferenceMemory.fst(header:const.prefix(length),fileBytes:1000)}
        check(true,"every truncated OpenFst header is handled without an out-of-bounds read")
        let models=base.appendingPathComponent("model");try FileManager.default.createDirectory(at:models,withIntermediateDirectories:true)
        try const.write(to:models.appendingPathComponent("HCLG.fst"));try Data(repeating:0,count:20).write(to:models.appendingPathComponent("final.mdl"))
        let budget=try NagramiXLocalInferenceMemory.vosk(at:models)
        check(budget==16*mib+10*32+30*16+80+384*mib,"Vosk budget uses installed FST/matrix bytes and decoder reserve")
        try FileManager.default.createSymbolicLink(at:models.appendingPathComponent("linked"),withDestinationURL:models.appendingPathComponent("HCLG.fst"))
        failure(.storage,"model scan rejects links"){_ = try NagramiXLocalInferenceMemory.vosk(at:models)}
        try FileManager.default.removeItem(at:models.appendingPathComponent("linked"))
        failure(.storage,"missing model directory fails closed"){_ = try NagramiXLocalInferenceMemory.vosk(at:base.appendingPathComponent("absent"))}
        let media=try NagramiXTranscriptionMedia(base.appendingPathComponent("media"))
        let floats=(0..<20000).map{Float($0)/20000};let bytes=floats.withUnsafeBytes{Data($0)}
        PCMBoundary.reset([bytes,bytes])
        let samples=try media.withPCM(cancellation:NagramiXTranscriptionCancellation()){Array($0)}
        check(samples==floats+floats,"mapped PCM preserves exact samples and order across decoded buffers")
        check(PCMBoundary.copySizes.max()!<=65536,"temporary PCM copies are bounded at 64KB")
        check(try FileManager.default.contentsOfDirectory(atPath:media.directory.path).isEmpty,"PCM scratch removed after mapped-buffer lease ends")
        let token=NagramiXTranscriptionCancellation();PCMBoundary.reset([bytes]);PCMBoundary.cancelOnCopy=token
        failure(.cancelled,"cancel during multi-chunk copy stops decoding"){try media.withPCM(cancellation:token){_ in ()}}
        check(try FileManager.default.contentsOfDirectory(atPath:media.directory.path).isEmpty,"cancelled PCM scratch removed")
        PCMBoundary.reset([bytes]);PCMBoundary.copyFailure=true
        failure(.unavailableMedia,"decoder copy failure propagates"){try media.withPCM(cancellation:NagramiXTranscriptionCancellation()){_ in ()}}
        PCMBoundary.reset([]);PCMBoundary.blocks=[PCMBlock(Data(),length:16000*901*4)]
        failure(.tooLarge,"oversized PCM rejected before copying"){try media.withPCM(cancellation:NagramiXTranscriptionCancellation()){_ in ()}}
        PCMBoundary.reset([])
        failure(.unavailableMedia,"empty PCM rejected"){try media.withPCM(cancellation:NagramiXTranscriptionCancellation()){_ in ()}}
        PCMBoundary.reset([bytes]);PCMBoundary.readerFailure=true
        failure(.unavailableMedia,"truncated decoding cannot produce a successful transcript"){try media.withPCM(cancellation:NagramiXTranscriptionCancellation()){_ in ()}}
        var config=NagramiXTranscriptionConfiguration();config.whisper = .medium;config.language="ru";config.whisperLanguage="auto"
        PCMBoundary.reset([bytes]);NativeBoundary.reset();boundaryMemory=5*1024*mib
        check(try result(.whisper,media,config).get()=="hello","real Whisper orchestration passes corrected admission budget")
        check(NativeBoundary.modelPath.hasSuffix(config.whisper.fileName) && NativeBoundary.language=="auto","selected model and language are never downgraded")
        check(NativeBoundary.destroyed==1 && NativeBoundary.freed==1 && NagramiXWhisperModels.shared.activeLeases==0,"Whisper output and native/model leases released before callback")
        NativeBoundary.reset();PCMBoundary.reset([bytes]);boundaryMemory=100*mib
        if case .failure(.insufficientMemory)=result(.whisper,media,config){check(NativeBoundary.calls==0 && PCMBoundary.copySizes.isEmpty,"real low headroom refuses before audio decoding or native allocation")}else{check(false,"memory refusal")}
        boundaryMemory=5*1024*mib;PCMBoundary.reset([bytes]);PCMBoundary.memoryOnCopy=100*mib
        if case .failure(.insufficientMemory)=result(.whisper,media,config){check(NativeBoundary.calls==0,"falling headroom during PCM preparation prevents native allocation")}else{check(false,"second memory check")}
        check(try FileManager.default.contentsOfDirectory(atPath:media.directory.path).isEmpty,"second memory refusal releases PCM scratch")
        PCMBoundary.reset([bytes])
        boundaryMemory=5*1024*mib;NativeBoundary.reset();NativeBoundary.code=4
        if case .failure(.insufficientMemory)=result(.whisper,media,config){check(NativeBoundary.destroyed==1 && NativeBoundary.freed==1,"native bad_alloc maps to memory error with cleanup")}else{check(false,"native memory error")}
        NagramiXVoskModels.shared.path=models;config.language="ru";config.voskModelID="vosk-model-ru-0.42";NativeBoundary.reset()
        check(try result(.vosk,media,config).get()=="first second","real Vosk orchestration keeps endpoint fragments and uses installed-file budget")
        check(NativeBoundary.modelPath==models.path && NativeBoundary.freed==1 && NagramiXVoskModels.shared.activeLeases==0,"selected Vosk model and leases preserved")
        config.voskModelID=nil
        check(NagramiXTranscriptionVosk.model(config)?.type=="small","default Vosk selection prefers the universal mobile model")
        config.voskModelID="vosk-model-ru-0.42"
        check(NagramiXTranscriptionVosk.model(config)?.name==config.voskModelID,"explicit legacy Vosk choice remains readable")
        config.voskModelID="vosk-model-ru-0.10-lgraph"
        check(NagramiXTranscriptionVosk.model(config)?.name==config.voskModelID,"verified graph alternative resolves by explicit ID")
        check(NagramiXVoskModel.all.filter{$0.lang=="ru"}.count==3,"existing Russian entries are preserved and one archived graph model is appended")
        check(NagramiXVoskModel.all.filter{$0.lang=="en-us"}.count>2,"Vosk variants depend on language")
        print("\(count) actual local ASR budget/PCM/orchestration checks passed; AVFoundation, native inference and OS headroom are explicit boundaries")
    }
}
