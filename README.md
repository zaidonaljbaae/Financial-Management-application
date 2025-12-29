# Money Manager (Financial Management App)

A desktop **Financial Management application** built with **Python**, **Tkinter**, and **SQLite**.  
This app allows users to manage accounts, track income and expenses, visualize data, and securely protect access with passwords.

---

## 🚀 Features

- Desktop GUI using **Tkinter**
- Local **SQLite** database
- Account management (active / inactive)
- Transaction management (income & expenses)
- Color-coded transactions (positive / negative / category-based)
- Dashboard with summaries and charts
- CSV import and export
- Built-in calculator
- Theme and UI customization
- Application-level security with password protection

---

## 🔐 Security

The application uses **two passwords**:
- **Program password**
- **Database password**

Passwords are securely stored using **PBKDF2 hashing** in:
```
data/security.json
```

### Protection mechanism
- After **10 failed login attempts**, all local data is deleted:
  - `finance.db`
  - `ui_prefs.json`
  - `security.json`

⚠️ Note: This protects the app interface. SQLite files are still local and can be copied if accessed directly.

---

## 📁 Project Structure

```
Financial_Management_app/
│
├── app.py
├── requirements.txt
├── assets/
│   └── logo.jpg
├── data/
│   ├── finance.db
│   ├── security.json
│   └── ui_prefs.json
├── finance/
│   ├── db.py
│   ├── prefs.py
│   └── security.py
└── ui/
    ├── app.py
    ├── auth.py
    ├── settings_window.py
    └── pages/
        ├── dashboard.py
        ├── accounts.py
        └── transactions.py
```

---

## 🧰 Requirements

- Python **3.10+**
- Tkinter (included with most Python installations)

Python dependencies:
- pandas
- numpy
- matplotlib

Install them with:
```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
python app.py
```

---

## 📦 Build as Desktop Application

You can package the app using **PyInstaller**.

### Install PyInstaller
```bash
python -m pip install pyinstaller
```

### Build (recommended: one-folder mode)

**Windows**
```bash
pyinstaller --noconsole --onedir --name MoneyManager ^
 --add-data "assets;assets" app.py
```

**macOS / Linux**
```bash
pyinstaller --noconsole --onedir --name MoneyManager \
  --add-data "assets:assets" app.py
```

The executable will be located in:
```
dist/MoneyManager/
```

⚠️ One-file mode is not recommended because the app writes local data files.

---

## 💾 Data & Backup

User data is stored locally:
- `data/finance.db`

To back up your data, simply copy this file.

---

## 📄 License

This project is for educational and personal use.  
You may add an MIT License if you plan to distribute it publicly.

---

## ✨ Author

Developed using Python for personal financial management and learning purposes.


pyinstaller --onefile --noconsole --name MoneyManager --add-data "assets;assets" app.py
