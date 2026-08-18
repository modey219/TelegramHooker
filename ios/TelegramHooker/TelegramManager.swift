import Foundation

enum TelegramError: Error, LocalizedError {
    case notConnected
    case invalidCredentials
    case sessionExpired

    var errorDescription: String? {
        switch self {
        case .notConnected: return "Not connected to Telegram"
        case .invalidCredentials: return "Invalid API credentials"
        case .sessionExpired: return "Session expired, please login again"
        }
    }
}

class TelegramManager {
    static let shared = TelegramManager()
    private init() {}

    var isConnected = false
    var currentUser: String?

    func connect(apiId: String, apiHash: String, phone: String, completion: @escaping (Result<Void, Error>) -> Void) {
        guard let id = Int(apiId) else {
            completion(.failure(TelegramError.invalidCredentials))
            return
        }

        let config: [String: Any] = ["api_id": id, "api_hash": apiHash, "phone": phone]
        if let data = try? JSONSerialization.data(withJSONObject: config) {
            UserDefaults.standard.set(data, forKey: "config")
        }

        DispatchQueue.global().asyncAfter(deadline: .now() + 1) {
            self.isConnected = true
            self.currentUser = phone
            completion(.success(()))
        }
    }

    func disconnect() {
        isConnected = false
        currentUser = nil
    }
}
