import Foundation

enum AppError: Error, LocalizedError {
    case notConnected
    case invalidCredentials
    case networkError(String)
    case sessionExpired

    var errorDescription: String? {
        switch self {
        case .notConnected: return "Not connected to Telegram"
        case .invalidCredentials: return "Invalid API credentials. Check my.telegram.org"
        case .networkError(let msg): return "Network error: \(msg)"
        case .sessionExpired: return "Session expired. Please login again"
        }
    }
}

class TelegramManager {
    static let shared = TelegramManager()
    private init() {}

    private(set) var isConnected = false
    private(set) var currentUser: String?

    func connect(apiId: String, apiHash: String, phone: String, completion: @escaping (Result<Void, Error>) -> Void) {
        guard let _ = Int(apiId) else {
            completion(.failure(AppError.invalidCredentials))
            return
        }

        let config: [String: Any] = ["api_id": apiId, "api_hash": apiHash, "phone": phone]
        if let data = try? JSONSerialization.data(withJSONObject: config) {
            UserDefaults.standard.set(data, forKey: "config")
            UserDefaults.standard.synchronize()
        }

        DispatchQueue.global().asyncAfter(deadline: .now() + 2) {
            self.isConnected = true
            self.currentUser = phone
            completion(.success(()))
        }
    }

    func restoreSession(completion: @escaping (Result<Void, Error>) -> Void) {
        guard let data = UserDefaults.standard.data(forKey: "config"),
              let _ = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            completion(.failure(AppError.sessionExpired))
            return
        }

        DispatchQueue.global().asyncAfter(deadline: .now() + 1) {
            self.isConnected = true
            self.currentUser = "Restored"
            completion(.success(()))
        }
    }

    func sendMessage(target: String, text: String, completion: @escaping (Result<Void, Error>) -> Void) {
        guard isConnected else {
            completion(.failure(AppError.notConnected))
            return
        }

        DispatchQueue.global().asyncAfter(deadline: .now() + 1) {
            completion(.success(()))
        }
    }

    func disconnect() {
        isConnected = false
        currentUser = nil
        UserDefaults.standard.removeObject(forKey: "config")
    }
}
