# 📧 Bulk Google Workspace User Generator

Easily create Google Workspace users in bulk via GitHub Actions, using a `.txt` file and a custom email HTML template.

---

## 🌐 Live Domain

**Currently Active Domain:** `a1.eaudemathematica.blog`

---

## 🧾 How It Works

1. Push a `.txt` file with user info to the `requests/` folder in your repository.
2. A GitHub Action automatically triggers.
3. The script reads the data, creates a user in your Google Workspace organization.
4. The new user receives a beautifully styled HTML email with credentials.

---

## 📄 `.txt` File Format

Create a file like `requests/username.txt`:

```
primaryEmail: yourusername@a1.eaudemathematica.blog
givenName: Your
familyName: Name
recoveryEmail:
recoveryPhone:
orgUnitPath: /
EmailToSendCred:
```

🔹 **Required fields:**

* `primaryEmail`: Full email address to be created.
* `givenName`: First name of the user.
* `EmailToSendCred`: Where to send login credentials.

🔹 **Optional fields:**

* `familyName`
* `recoveryEmail`
* `recoveryPhone`
* `orgUnitPath` (default is `/`)

---

## 📬 Features

* ✅ Automated user creation using Google Admin SDK.
* 📩 Sends credentials using a professional HTML email template.
* 🔐 Uses OAuth2 credentials securely via GitHub Secrets.
* 🛠️ Customizable email templates using Python `string.Template` syntax.

---

## ⚙️ Setup Instructions

1. Clone this repo.
2. Set up your Google Admin OAuth2 client and generate `token.json`.
3. Add secrets in your GitHub repository:

   * `CLIENT_SECRET_JSON`
   * `TOKEN_JSON`
   * `EMAIL_SMTP_USER`
   * `EMAIL_SMTP_PASS`
4. Push a `.txt` file in the `requests/` folder to trigger the workflow.

---

## 📁 File Structure

```
├── create_user_from_txt.py          # Main script
├── templates/
│   └── email_template.html          # Email HTML template
├── requests/
│   └── sample_user.txt              # Sample user data file
├── .github/
│   └── workflows/
│       └── create_user.yml          # GitHub Action to trigger automation
```

---

## 🙋‍♂️ Need Help?

* Make sure the domain is verified and Google Admin API is enabled.
* Ensure you're the administrator of the domain.
* Check the logs in GitHub Actions for any errors.

---

## 📜 License

MIT License

---

Made with ❤️ by [Anshu Verma](https://github.com/anshuverma-design) — Automate your Google Workspace onboarding today!
