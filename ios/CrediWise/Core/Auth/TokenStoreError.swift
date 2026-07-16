import Security

enum TokenStoreError: Error, Equatable {
    case invalidData
    case unexpectedStatus(OSStatus)
}
