import Foundation

actor APIFinancingNeedRepository: FinancingNeedRepository {
    private let baseURL: URL
    private let session: any HTTPDataSession
    private let authInterceptor: AuthInterceptor
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(
        baseURL: URL,
        session: any HTTPDataSession = URLSession.shared,
        authInterceptor: AuthInterceptor
    ) {
        self.baseURL = baseURL
        self.session = session
        self.authInterceptor = authInterceptor
    }

    func save(_ need: FinancingNeed) async throws -> FinancingNeedReceipt {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/financing-needs"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        do {
            request.httpBody = try encoder.encode(FinancingNeedRequest(need: need))
        } catch {
            throw FinancingNeedRepositoryError.unavailable
        }

        let data = try await execute(request, expectedStatus: 201)
        do {
            let response = try decoder.decode(FinancingNeedResponse.self, from: data)
            return FinancingNeedReceipt(financingNeedID: response.financingNeedID.uuidString)
        } catch {
            throw FinancingNeedRepositoryError.unavailable
        }
    }

    private func execute(_ request: URLRequest, expectedStatus: Int) async throws -> Data {
        var authorizedRequest: URLRequest
        do {
            authorizedRequest = try await authInterceptor.authorize(request)
        } catch {
            throw FinancingNeedRepositoryError.unavailable
        }
        var retryCount = 0
        while true {
            let data: Data
            let response: URLResponse
            do {
                (data, response) = try await session.response(for: authorizedRequest)
            } catch is CancellationError {
                throw CancellationError()
            } catch {
                throw FinancingNeedRepositoryError.unavailable
            }
            guard let httpResponse = response as? HTTPURLResponse else {
                throw FinancingNeedRepositoryError.unavailable
            }
            do {
                if let retry = try await authInterceptor.requestForRetry(
                    authorizedRequest,
                    statusCode: httpResponse.statusCode,
                    retryCount: retryCount
                ) {
                    authorizedRequest = retry
                    retryCount += 1
                    continue
                }
            } catch {
                throw FinancingNeedRepositoryError.unavailable
            }
            guard httpResponse.statusCode == expectedStatus else {
                throw FinancingNeedRepositoryError.unavailable
            }
            return data
        }
    }
}

private struct FinancingNeedRequest: Encodable {
    let requestedAmount: Int64
    let purpose: String
    let preferredTenorMonths: Int
    let urgency: String
    let notes: String?

    init(need: FinancingNeed) {
        requestedAmount = need.requestedAmount
        purpose = Self.purpose(need.purpose)
        preferredTenorMonths = need.preferredTenorMonths
        urgency = need.urgency.rawValue.uppercased()
        notes = need.notes.isEmpty ? nil : need.notes
    }

    enum CodingKeys: String, CodingKey {
        case requestedAmount = "requested_amount"
        case purpose
        case preferredTenorMonths = "preferred_tenor_months"
        case urgency
        case notes
    }

    private static func purpose(_ purpose: FinancingNeed.Purpose) -> String {
        switch purpose {
        case .medical: return "MEDICAL"
        case .education: return "EDUCATION"
        case .householdEmergency: return "HOUSEHOLD_EMERGENCY"
        case .productiveBusiness: return "PRODUCTIVE_BUSINESS"
        case .equipment: return "EQUIPMENT"
        case .workingCapital: return "WORKING_CAPITAL"
        case .vehicleDeviceRepair: return "VEHICLE_DEVICE_REPAIR"
        }
    }
}

private struct FinancingNeedResponse: Decodable {
    let financingNeedID: UUID

    enum CodingKeys: String, CodingKey {
        case financingNeedID = "financing_need_id"
    }
}
