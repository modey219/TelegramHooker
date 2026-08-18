import UIKit

class MainViewController: UIViewController {
    private let callLabel = UILabel()
    private let micLabel = UILabel()
    private let targetField = UITextField()
    private let logLabel = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.06, green: 0.06, blue: 0.12, alpha: 1)
        title = "Telegram Hooker"
        navigationController?.navigationBar.tintColor = UIColor(red: 0.3, green: 0.7, blue: 1, alpha: 1)
        setupUI()
    }

    private func setupUI() {
        let headerLabel = UILabel()
        headerLabel.text = "TELEGRAM HOOKER v1.0"
        headerLabel.font = .systemFont(ofSize: 20, weight: .bold)
        headerLabel.textColor = UIColor(red: 0.3, green: 0.7, blue: 1, alpha: 1)
        headerLabel.textAlignment = .center

        callLabel.text = "Not in call"
        callLabel.font = .systemFont(ofSize: 14)
        callLabel.textColor = .gray
        callLabel.textAlignment = .center

        micLabel.text = "Muted"
        micLabel.font = .systemFont(ofSize: 14)
        micLabel.textColor = .red
        micLabel.textAlignment = .center

        targetField.placeholder = "Group ID or @username"
        targetField.font = .systemFont(ofSize: 15)
        targetField.borderStyle = .roundedRect
        targetField.textColor = .white
        targetField.backgroundColor = UIColor(red: 0.15, green: 0.15, blue: 0.25, alpha: 1)
        targetField.layer.cornerRadius = 8
        targetField.heightAnchor.constraint(equalToConstant: 44).isActive = true

        let joinBtn = makeButton("JOIN VOICE CALL", color: UIColor(red: 0.2, green: 0.8, blue: 0.4, alpha: 1), action: #selector(joinTapped))
        let muteBtn = makeButton("MUTE", color: UIColor(red: 1, green: 0.3, blue: 0.3, alpha: 1), action: #selector(muteTapped))
        let unmuteBtn = makeButton("UNMUTE", color: UIColor(red: 1, green: 0.85, blue: 0.2, alpha: 1), action: #selector(unmuteTapped))
        let leaveBtn = makeButton("LEAVE CALL", color: UIColor(red: 0.6, green: 0.2, blue: 0.2, alpha: 1), action: #selector(leaveTapped))

        let muteRow = UIStackView(arrangedSubviews: [muteBtn, unmuteBtn])
        muteRow.axis = .horizontal
        muteRow.spacing = 10
        muteRow.distribution = .fillEqually

        logLabel.text = "Ready"
        logLabel.font = .systemFont(ofSize: 12)
        logLabel.textColor = .gray
        logLabel.numberOfLines = 0

        let stack = UIStackView(arrangedSubviews: [headerLabel, callLabel, micLabel, targetField, joinBtn, muteRow, leaveBtn, logLabel])
        stack.axis = .vertical
        stack.spacing = 10
        stack.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
        ])
    }

    private func makeButton(_ title: String, color: UIColor, action: Selector) -> UIButton {
        let btn = UIButton(type: .system)
        btn.setTitle(title, for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 16, weight: .bold)
        btn.backgroundColor = color
        btn.setTitleColor(.white, for: .normal)
        btn.layer.cornerRadius = 10
        btn.heightAnchor.constraint(equalToConstant: 50).isActive = true
        btn.addTarget(self, action: action, for: .touchUpInside)
        return btn
    }

    @objc private func joinTapped() {
        guard let target = targetField.text, !target.isEmpty else {
            logLabel.text = "Enter a group ID"
            return
        }
        logLabel.text = "Joining..."
        VoiceCallManager.shared.join(target: target) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    self?.callLabel.text = "In call"
                    self?.callLabel.textColor = .green
                    self?.micLabel.text = "Muted"
                    self?.micLabel.textColor = .red
                    self?.logLabel.text = "Joined call"
                case .failure(let err):
                    self?.logLabel.text = "Error: \(err.localizedDescription)"
                }
            }
        }
    }

    @objc private func muteTapped() {
        VoiceCallManager.shared.mute()
        micLabel.text = "Muted"
        micLabel.textColor = .red
    }

    @objc private func unmuteTapped() {
        VoiceCallManager.shared.unmute()
        micLabel.text = "Unmuted"
        micLabel.textColor = .green
    }

    @objc private func leaveTapped() {
        VoiceCallManager.shared.leave()
        callLabel.text = "Not in call"
        callLabel.textColor = .gray
        logLabel.text = "Left call"
    }
}
