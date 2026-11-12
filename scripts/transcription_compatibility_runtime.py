"""Complete Premium ASR fixture with the native IUO error boundary and nil failures."""
import premium_temporary_transcription_runtime as premium


def fixture(source):
    code=premium.fixture(source)
    old='struct RpcError:Error {let errorDescription:String}'
    assert code.count(old)==1
    code=code.replace(old,'struct RpcError:Error {let errorDescription:String!}',1)
    old='var error:String?;var name=""'
    assert code.count(old)==1
    code=code.replace(old,'var error:String?;var forceError=false;var name=""',1)
    old='if let error {f?(.failure(RpcError(errorDescription:error)))}'
    assert code.count(old)==1
    code=code.replace(old,'if forceError || error != nil {f?(.failure(RpcError(errorDescription:error)))}',1)
    marker='  for (flags,text,error) in '
    assert code.count(marker)==1
    tests='''  let nullableErrors:[(String?,NagramiXTranscriptionFailure)] = [(nil,.network),("",.network),("FLOOD_PREMIUM_WAIT_30",.quota),("FILE_TOO_BIG",.tooLarge),("METHOD_NOT_AVAILABLE",.unavailableMedia)]
  for (description,error) in nullableErrors {
   configure();UploadBoundary.reset();let c=context(),m=message(c);c.account.network.file.forceError=true;c.account.network.file.error=description
   expectFile(run(c,m) == .failure(error),"nullable RPC error preserves classification")
   expectFile(AudioBoundary.provider==nil,"nullable RPC error never selects Apple");original(c,m)
  }
'''
    return code.replace(marker,tests+marker,1)


def negatives(code):
    yield from premium.negatives(code)
    old='let description = error.errorDescription ?? ""'
    assert code.count(old)==1
    yield ('nil-classified-as-quota',code.replace(old,'let description = error.errorDescription ?? "FLOOD_WAIT_0"',1),'nullable RPC error preserves classification')
