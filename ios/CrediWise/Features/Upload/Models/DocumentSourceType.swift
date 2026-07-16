enum DocumentSourceType: String, Equatable, Sendable {
    case originalPDF = "ORIGINAL_PDF"
    case exportedCSV = "EXPORTED_CSV"
    case screenshot = "SCREENSHOT"
    case photo = "PHOTO"
}
