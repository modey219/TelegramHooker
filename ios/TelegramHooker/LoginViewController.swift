import UIKit

class LoginViewController: UIViewController {
    private let apiIdField = UITextField()
    private let apiHashField = UITextField()
    private let phoneField = UITextField()
    private let statusLabel = UILabel()
    private let activityIndicator = UIActivityIndicatorView(style: .medium)

    private let accentColor = UIColor(red: 0.3, green: 0.7, blue: 1, alpha: 1)
    private let bgColor = UIColor(red: 0.06, green: 0.06, blue: 0.12, alpha: 1)
    private let inputBg = UIColor(red: 0.15, green: 0.15, blue: 0.25, alpha: 1)

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = bgColor
        title = "Telegram Hooker"
        setupUI()
        loadSavedConfig()
        hideKeyboardOnTap()
    }

    private func setupUI() {
        let titleLabel = UILabel()
        titleLabel.text = "TELEGRAM HOOKER"
        titleLabel.font = .systemFont(ofSize: 28, weight: .bold)
        titleLabel.textColor = accentColor
        titleLabel.textAlignment = .center

        let authorLabel = UILabel()
        authorLabel.text = "By: @ASEQX12  |  v1.0 iOS"
        authorLabel.font = .systemFont(ofSize: 13)
        authorLabel.textColor = .gray
        authorLabel.textAlignment = .center

        configureField(apiIdField, placeholder: "API ID", keyboardType: .numberPad)
        configureField(apiHashField, placeholder: "API Hash")
        configureField(phoneField, placeholder: "+1234567890", keyboardType: .phonePad)

        let loginButton = makeButton("LOGIN", color: UIColor(red: 0.2, green: 0.8, blue: 0.4, alpha: 1))
        loginButton.addTarget(self, action: #selector(loginTapped), for: .touchUpInside)

        let restoreButton = makeButton("RESTORE SESSION", color: accentColor)
        restoreButton.addTarget(self, action: #selector(restoreTapped), for: .touchUpInside)

        statusLabel.font = .systemFont(ofSize: 13)
        statusLabel.textColor = .yellow
        statusLabel.textAlignment = .center
        statusLabel.numberOfLines = 0

        activityIndicator.color = accentColor
        activityIndicator.hidesWhenStopped = true

        let stack = UIStackView(arrangedSubviews: [
            titleLabel, authorLabel,
            makeSpacer(), apiIdField, apiHashField, phoneField,
            loginButton, restoreButton, activityIndicator, statusLabel
        ])
        stack.axis = .vertical
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor, constant: -30),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 30),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -30),
        ])
    }

    private func configureField(_ field: UITextField, placeholder: String, keyboardType: UIKeyboardType = .default) {
        field.placeholder = placeholder
        field.font = .monospacedSystemFont(ofSize: 15, weight: .regular)
        field.borderStyle = .none
        field.keyboardType = keyboardType
        field.textColor = .white
        field.backgroundColor = inputBg
        field.layer.cornerRadius = 10
        field.layer.borderWidth = 1
        field.layer.borderColor = UIColor(white: 0.3, alpha: 0.5).cgColor
        field.autocapitalizationType = .none
        field.autocorrectionType = .no
        let padding = UIView(frame: CGRect(x: 0, y: 0, width: 12, height: 44))
        field.leftView = padding
        field.leftViewMode = .always
        field.heightAnchor.constraint(equalToConstant: 48).isActive = true
    }

    private func makeButton(_ title: String, color: UIColor) -> UIButton {
        let btn = UIButton(type: .system)
        btn.setTitle(title, for: .normal)
        btn.titleLabel?.font = .systemFont(ofSize: 17, weight: .bold)
        btn.backgroundColor = color
        btn.setTitleColor(.white, for: .normal)
        btn.layer.cornerRadius = 12
        btn.heightAnchor.constraint(equalToConstant: 52).isActive = true
        return btn
    }

    private func makeSpacer() -> UIView {
        let v = UIView(frame: CGRect(x: 0, y: 0, width: 1, height: 20))
        v.heightAnchor.constraint(equalToConstant: 20).isActive = true
        return v
    }

    private func hideKeyboardOnTap() {
        let tap = UITapGestureRecognizer(target: view, action: #selector(UIView.endEditing))
        tap.cancelsTouchesInView = false
        view.addGestureRecognizer(tap)
    }

    private func loadSavedConfig() {
        if let data = UserDefaults.standard.data(forKey: "config"),
           let cfg = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            apiIdField.text = cfg["api_id"] as? String
            apiHashField.text = cfg["api_hash"] as? String
            phoneField.text = cfg["phone"] as? String
        }
    }

    @objc private func loginTapped() {
        view.endEditing(true)
        guard let apiId = apiIdField.text, !apiId.isEmpty,
              let apiHash = apiHashField.text, !apiHash.isEmpty,
              let phone = phoneField.text, !phone.isEmpty else {
            statusLabel.text = "Please fill all fields"
            return
        }
        statusLabel.text = "Connecting to Telegram..."
        activityIndicator.startAnimating()

        TelegramManager.shared.connect(apiId: apiId, apiHash: apiHash, phone: phone) { [weak self] result in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()
                switch result {
                case .success:
                    self?.statusLabel.textColor = .green
                    self?.statusLabel.text = "Connected!"
                    let main = MainViewController()
                    self?.navigationController?.pushViewController(main, animated: true)
                case .failure(let err):
                    self?.statusLabel.textColor = .red
                    self?.statusLabel.text = err.localizedDescription
                }
            }
        }
    }

    @objc private func restoreTapped() {
        statusLabel.text = "Restoring session..."
        activityIndicator.startAnimating()
        TelegramManager.shared.restoreSession { [weak self] result in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()
                switch result {
                case .success:
                    self?.statusLabel.textColor = .green
                    self?.statusLabel.text = "Session restored!"
                    let main = MainViewController()
                    self?.navigationController?.pushViewController(main, animated: true)
                case .failure(let err):
                    self?.statusLabel.textColor = .red
                    self?.statusLabel.text = err.localizedDescription
                }
            }
        }
    }
}
