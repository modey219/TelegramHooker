import Foundation

class VoiceCallManager {
    static let shared = VoiceCallManager()
    private init() {}

    private(set) var inCall = false
    private(set) var isMuted = true
    private var currentTarget: String?

    func join(target: String, completion: @escaping (Result<Void, Error>) -> Void) {
        guard TelegramManager.shared.isConnected else {
            completion(.failure(AppError.notConnected))
            return
        }

        DispatchQueue.global().asyncAfter(deadline: .now() + 2) { [weak self] in
            self?.inCall = true
            self?.isMuted = true
            self?.currentTarget = target
            completion(.success(()))
        }
    }

    func leave() {
        inCall = false
        isMuted = true
        currentTarget = nil
    }

    func mute() {
        guard inCall else { return }
        isMuted = true
    }

    func unmute() {
        guard inCall else { return }
        isMuted = false
    }
}
