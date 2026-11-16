// Photos callback IO. Chunk writes, locks, pinning and disposal are the actual exporter.
final class PHAssetResourceManager {
 static let shared=PHAssetResourceManager()
 static func `default`()->PHAssetResourceManager{shared}
 struct Request {let resource:PHAssetResource;let data:(Data)->Void;let completion:(Error?)->Void}
 private let lock=NSLock()
 private var pending:[Int:Request]=[:],nextId=0,requestCount=0,cancelCount=0
 var requests:Int{lock.lock();defer{lock.unlock()};return requestCount}
 var cancelled:Int{lock.lock();defer{lock.unlock()};return cancelCount}
 func requestData(for resource:PHAssetResource,options:PHAssetResourceRequestOptions,dataReceivedHandler:@escaping(Data)->Void,completionHandler:@escaping(Error?)->Void)->Int {
  precondition(options.isNetworkAccessAllowed);lock.lock();defer{lock.unlock()};nextId+=1;requestCount+=1
  pending[nextId]=Request(resource:resource,data:dataReceivedHandler,completion:completionHandler);return nextId
 }
 func cancelDataRequest(_ id:Int){lock.lock();cancelCount+=1;pending.removeValue(forKey:id);lock.unlock()}
 func finish(_ error:Error?=nil){
  lock.lock();let values=pending;pending.removeAll();lock.unlock()
  for request in values.values {
   let bytes=request.resource.bytes
   for offset in stride(from:0,to:bytes.count,by:137){request.data(bytes.subdata(in:offset..<min(offset+137,bytes.count)))}
   request.completion(error)
  }
 }
}
