"""Typecheck exact error classification against the native MTRpcError header."""
import hashlib,subprocess,sys
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan

TRANSPORT='submodules/TelegramCore/Sources/TelegramEngine/Messages/Transcription.swift'
HEADER='submodules/MtProtoKit/PublicHeaders/MtProtoKit/MTRpcError.h'


def classification(text):
    method=block(text,'    func nagramiXTranscribeAudioFile(')
    start=method.index('                        let description = error.errorDescription')
    end=method.index('\n                    }',start)
    return method[start:end]


def check(source,swiftc,folder):
    plan=checked_plan('release_096_transcription_compatibility')
    header=source/HEADER
    assert hashlib.sha256(header.read_bytes()).hexdigest()==plan['guards'][HEADER]
    assert '@property (nonatomic, strong, readonly) NSString *errorDescription;' in header.read_text()
    signature=block((source/'submodules/TelegramCore/Sources/Network/Network.swift').read_text(),'    func request<T>(').split('{',1)[0]
    assert 'Signal<T, MTRpcError>' in signature
    text=(source/TRANSPORT).read_text()
    enum=block(text,'public enum EngineAudioFileTranscriptionError:')
    body=classification(text)
    assert 'let description = error.errorDescription ?? ""' in body
    folder.mkdir(parents=True,exist_ok=True)
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-typecheck','-module-cache-path',str(folder/'cache')]
    if sys.platform=='darwin':
        module=folder/'native-header';module.mkdir()
        (module/'module.modulemap').write_text('module NagramiXNativeRpcError { header "'+str(header)+'" export * }\n')
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
        common+=['-sdk',sdk,'-target','arm64-apple-ios15.0','-I',str(module)]
        boundary='import NagramiXNativeRpcError\n'
        kind='actual unchanged Objective-C MTRpcError.h imported by iPhoneOS SDK, arm64 iOS15'
    else:
        boundary='struct MTRpcError {let errorDescription:String!}\n'
        kind='explicit IUO adapter on Linux; native Objective-C importer pending Apple'
    support='''import Foundation
struct Signal<Value,ErrorType> {static func single(_ value:Value)->Self {Self()}}
enum MultipartUploadError:Error {case generic}
'''
    code=support+boundary+enum+'\nfunc classify(_ error:MTRpcError)->Signal<Result<String,EngineAudioFileTranscriptionError>,MultipartUploadError> {\n'+body+'\n}\n'
    positive=folder/'classification-final62.swift';positive.write_text(code)
    result=subprocess.run(common+[str(positive)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    old=code.replace('let description = error.errorDescription ?? ""','let description = error.errorDescription',1)
    assert old!=code
    negative=folder/'classification-original205.swift';negative.write_text(old)
    result=subprocess.run(common+[str(negative)],capture_output=True,text=True,timeout=120)
    assert result.returncode!=0 and 'must be unwrapped' in result.stderr and 'hasPrefix' in result.stderr,result.stdout+result.stderr
    return {'status':'passed','boundary':kind,'header_sha256':plan['guards'][HEADER],'original205_reproduced_and_rejected':True,'classification_body':'exact production lines; Signal is an explicit output-only type adapter','whole_engine_fixture':'separate full production ASR/Engine/Coordinator runtime with IUO and nil failures','full_application_sdk':'pending','device':'pending'}
