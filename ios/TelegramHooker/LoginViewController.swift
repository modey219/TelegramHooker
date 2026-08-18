import UIKit

class LoginViewController: UIViewController {
    private let titleLabel = UILabel()
    private let apiIdField = UITextField()
    private let apiHashField = UITextField()
    private let phoneField = UITextField()
    private let loginButton = UIButton(type: .system)
    private let statusLabel = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.06, green: 0.06, blue: 0.12, alpha: 1)
        setupUI()
    }

    private func setupUI() {
        titleLabel.text = "TELEGRAM HOOKER"
        titleLabel.font = .systemFont(ofSize: 26, weight: .bold)
        titleLabel.textColor = UIColor(red: 0.3, green: 0.7, blue: 1, alpha: 1)
        titleLabel.textAlignment = .center

        let fields = [
            makeField(placeholder: "API ID", tag: 0),
            makeField(placeholder: "API Hash", tag: 1),
            makeField(placeholder: "+1234567890", tag: 2),
        ]
        apiIdField = fields[0]
        apiHashField = fields[1]
        phoneField = fields[2]

        loginButton.setTitle("LOGIN", for: .normal)
        loginButton.titleLabel?.font = .systemFont(ofSize: 18, weight: .bold)
        loginButton.backgroundColor = UIColor(red: 0.2, green: 0.8, blue: 0.4, alpha: 1)
        loginButton.setTitleColor(.white, for: .normal)
        loginButton.layer.cornerRadius = 12
        loginButton.addTarget(self, action: #selector(loginTapped), for: .touchUpInside)

        statusLabel.font = .systemFont(ofSize: 13)
        statusLabel.textColor = .yellow
        statusLabel.textAlignment = .center
        statusLabel.numberOfLines = 0

        let stack = UIStackView(arrangedSubviews: [titleLabel, apiIdField, apiHashField, phoneField, loginButton, statusLabel])
        stack.axis = .vertical
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 30),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -30),
        ])

        loadConfig()
    }

    private func makeField(placeholder: String, tag: Int) -> UITextField {
        let field = UITextField()
        field.placeholder = placeholder
        field.font = .systemFont(ofSize: 16)
        field.borderStyle = .roundedRect
        field.keyboardType = tag == 0 ? .numberPad : .default
        field.tag = tag
        field.textColor = .white
        field.backgroundColor = UIColor(red: 0.15, green: 0.15, blue: 0.25, alpha: 1)
        field.layer.cornerRadius = 8
        field.heightAnchor.constraint(equalToConstant: 48).isActive = true
        return field
    }

    private func loadConfig() {
        if let data = UserDefaults.standard.data(forKey: "config"),
           let cfg = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            apiIdField.text = cfg["api_id"] as? String
            apiHashField.text = cfg["api_hash"] as? String
            phoneField.text = cfg["phone"] as? String
        }
    }

    @objc private func loginTapped() {
        guard let apiId = apiIdField.text, !apiId.isEmpty,
              let apiHash = apiHashField.text, !apiHash.isEmpty,
              let phone = phoneField.text, !phone.isEmpty else {
            statusLabel.text = "Fill all fields"
            return
        }
        statusLabel.text = "Connecting..."
        TelegramManager.shared.connect(apiId: apiId, apiHash: apiHash, phone: phone) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    self?.statusLabel.text = "Connected!"
                    let main = MainViewController()
                    self?.navigationController?.pushViewController(main, animated: true)
                case .failure(let err):
                    self?.statusLabel.text = "Error: \(err.localizedDescription)"
                }
            }
        }
    }
}
