    static func transcribeAudioFile(file: Api.InputFile) -> (FunctionDescription, Buffer, DeserializeFunctionResponse<Api.messages.TranscribedAudio>) {
        let _tlObject = TLObjectAllocate(TLApiFunctionConstructorAt(609))
        tlStoreReference(_tlObject, 24, file.tlObject)
        return tlFunction(_tlObject)
    }