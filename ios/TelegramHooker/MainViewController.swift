import UIKit

class MainViewController: UIViewController {
    private let callLabel = UILabel()
    private let micLabel = UILabel()
    private let targetField = UITextField()
    private let logLabel = UILabel()
    private let activityIndicator = UIActivityIndicatorView(style: .medium)

    private let accentColor = UIColor(red: 0.3, green: 0.7, blue: 1, alpha: 1)
    private let inputBg = UIColor(red: 0.15, green: 0.15, blue: 0.25, alpha: 1)

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.06, green: 0.06, blue: 0.12, alpha: 1)
        title = "Telegram Hooker"
        navigationItem.hidesBackButton = true
        setupUI()
        hideKeyboardOnTap()
    }

    private func setupUI() {
        let headerLabel = UILabel()
        headerLabel.text = "TELEGRAM HOOKER  v1.0"
        headerLabel.font = .systemFont(ofSize: 20, weight: .bold)
        headerLabel.textColor = accentColor
        headerLabel.textAlignment = .center

        let statusInfo = UILabel()
        if let name = TelegramManager.shared.currentUser {
            statusInfo.text = "Logged in: \(name)"
        } else {
            statusInfo.text = "Connected"
        }
        statusInfo.font = .systemFont(ofSize: 13)
        statusInfo.textColor = .green
        statusInfo.textAlignment = .center

        callLabel.text = "Not in call"
        callLabel.font = .systemFont(ofSize: 14)
        callLabel.textColor = .gray
        callLabel.textAlignment = .center

        micLabel.text = "Muted"
        micLabel.font = .systemFont(ofSize: 14)
        micLabel.textColor = .red
        micLabel.textAlignment = .center

        targetField.placeholder = "Group ID or @username"
        targetField.font = .monospacedSystemFont(ofSize: 15, weight: .regular)
        targetField.textColor = .white
        targetField.backgroundColor = inputBg
        targetField.layer.cornerRadius = 10
        targetField.layer.borderWidth = 1
        targetField.layer.borderColor = UIColor(white: 0.3, alpha: 0.5).cgColor
        targetField.autocapitalizationType = .none
        targetField.autocorrectionType = .no
        let padding = UIView(frame: CGRect(x: 0, y: 0, width: 12, height: 44))
        targetField.leftView = padding
        targetField.leftViewMode = .always
        targetField.heightAnchor.constraint(equalToConstant: 48).isActive = true

        let joinBtn = makeButton("JOIN VOICE CALL", color: UIColor(red: 0.2, green: 0.8, blue: 0.4, alpha: 1), action: #selector(joinTapped))
        let muteBtn = makeButton("MUTE", color: UIColor(red: 1, green: 0.3, blue: 0.3, alpha: 1), action: #selector(muteTapped))
        let unmuteBtn = makeButton("UNMUTE", color: UIColor(red: 1, green: 0.85, blue: 0.2, alpha: 1), action: #selector(unmuteTapped))
        let leaveBtn = makeButton("LEAVE CALL", color: UIColor(red: 0.6, green: 0.2, blue: 0.2, alpha: 1), action: #selector(leaveTapped))

        let muteRow = UIStackView(arrangedSubviews: [muteBtn, unmuteBtn])
        muteRow.axis = .horizontal
        muteRow.spacing = 10
        muteRow.distribution = .fillEqually

        let msgField = UITextField()
        msgField.placeholder = "Message to send..."
        msgField.font = .monospacedSystemFont(ofSize: 15, weight: .regular)
        msgField.textColor = .white
        msgField.backgroundColor = inputBg
        msgField.layer.cornerRadius = 10
        msgField.layer.borderWidth = 1
        msgField.layer.borderColor = UIColor(white: 0.3, alpha: 0.5).cgColor
        msgField.autocapitalizationType = .none
        msgField.autocorrectionType = .no
        let msgPadding = UIView(frame: CGRect(x: 0, y: 0, width: 12, height: 44))
        msgField.leftView = msgPadding
        msgField.leftViewMode = .always
        msgField.heightAnchor.constraint(equalToConstant: 48).isActive = true
        self._msgField = msgField

        let sendBtn = makeButton("SEND MESSAGE", color: accentColor, action: #selector(sendTapped))

        activityIndicator.color = accentColor
        activityIndicator.hidesWhenStopped = true

        logLabel.text = "Ready"
        logLabel.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        logLabel.textColor = .gray
        logLabel.numberOfLines = 0
        logLabel.textAlignment = .center

        let logoutBtn = makeButton("LOGOUT", color: UIColor(white: 0.25, alpha: 1), action: #selector(logoutTapped))
        logoutBtn.heightAnchor.constraint(equalToConstant: 40).isActive = true

        let stack = UIStackView(arrangedSubviews: [
            headerLabel, statusInfo, callLabel, micLabel,
            targetField, joinBtn, muteRow, leaveBtn,
            msgField, sendBtn, activityIndicator, logLabel, logoutBtn
        ])
        stack.axis = .vertical
        stack.spacing = 10
        stack.translatesAutoresizingMaskIntoConstraints = false

        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scroll)
        scroll.addSubview(stack)

        NSLayoutConstraint.activate([
            scroll.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scroll.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scroll.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            scroll.bottomAnchor.constraint(equalTo: view.bottomAnchor),

            stack.topAnchor.constraint(equalTo: scroll.topAnchor, constant: 20),
            stack.leadingAnchor.constraint(equalTo: scroll.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: scroll.trailingAnchor, constant: -20),
            stack.bottomAnchor.constraint(equalTo: scroll.bottomAnchor, constant: -20),
            stack.widthAnchor.constraint(equalTo: scroll.widthAnchor, constant: -40),
        ])
    }

    private var _msgField: UITextField?

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

    private func hideKeyboardOnTap() {
        let tap = UITapGestureRecognizer(target: view, action: #selector(UIView.endEditing))
        tap.cancelsTouchesInView = false
        view.addGestureRecognizer(tap)
    }

    @objc private func joinTapped() {
        view.endEditing(true)
        guard let target = targetField.text, !target.isEmpty else {
            logLabel.text = "Enter a group ID"
            return
        }
        logLabel.text = "Joining..."
        activityIndicator.startAnimating()

        VoiceCallManager.shared.join(target: target) { [weak self] result in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()
                switch result {
                case .success:
                    self?.callLabel.text = "In call"
                    self?.callLabel.textColor = .green
                    self?.micLabel.text = "Muted"
                    self?.micLabel.textColor = .red
                    self?.logLabel.text = "Joined call"
                    self?.logLabel.textColor = .green
                case .failure(let err):
                    self?.logLabel.text = err.localizedDescription
                    self?.logLabel.textColor = .red
                }
            }
        }
    }

    @objc private func muteTapped() {
        VoiceCallManager.shared.mute()
        micLabel.text = "Muted"
        micLabel.textColor = .red
        logLabel.text = "Mic muted"
    }

    @objc private func unmuteTapped() {
        VoiceCallManager.shared.unmute()
        micLabel.text = "Unmuted"
        micLabel.textColor = .green
        logLabel.text = "Mic unmuted"
    }

    @objc private func leaveTapped() {
        VoiceCallManager.shared.leave()
        callLabel.text = "Not in call"
        callLabel.textColor = .gray
        micLabel.text = "Muted"
        micLabel.textColor = .red
        logLabel.text = "Left call"
        logLabel.textColor = .gray
    }

    @objc private func sendTapped() {
        view.endEditing(true)
        guard let target = targetField.text, !target.isEmpty,
              let text = _msgField?.text, !text.isEmpty else {
            logLabel.text = "Enter target and message"
            return
        }
        logLabel.text = "Sending..."
        activityIndicator.startAnimating()

        TelegramManager.shared.sendMessage(target: target, text: text) { [weak self] result in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()
                switch result {
                case .success:
                    self?.logLabel.text = "Message sent!"
                    self?.logLabel.textColor = .green
                    self?._msgField?.text = ""
                case .failure(let err):
                    self?.logLabel.text = err.localizedDescription
                    self?.logLabel.textColor = .red
                }
            }
        }
    }

    @objc private func logoutTapped() {
        TelegramManager.shared.disconnect()
        navigationController?.popToRootViewController(animated: true)
    }
}
