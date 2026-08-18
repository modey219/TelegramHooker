import Foundation

class VoiceCallManager {
    static let shared = VoiceCallManager()
    private init() {}

    var inCall = false
    var isMuted = true

    func join(target: String, completion: @escaping (Result<Void, Error>) -> Void) {
        DispatchQueue.global().asyncAfter(deadline: .now() + 1) {
            self.inCall = true
            self.isMuted = true
            completion(.success(()))
        }
    }

    func leave() {
        inCall = false
        isMuted = true
    }

    func mute() {
        isMuted = true
    }

    func unmute() {
        isMuted = false
    }
}
