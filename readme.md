# Buyer Persona 

Buyer Persona is a professional-grade desktop application built with Python and PySide6. It leverages OpenAI's structured outputs (`json_schema`) to generate precise, highly detailed marketing buyer personas. The tool features multi-threaded API calls to keep the user interface responsive and includes an embedded SQLite database to persist your generated personas locally.

## ✨ Features

- **Modern GUI (PySide6):** Clean, structured desktop interface built with native Qt bindings.
- **Asynchronous Processing:** Multi-threaded backend execution (`QThread`) prevents interface freezing during API requests.
- **Strict JSON Enforcement:** Utilizes OpenAI's `json_schema` response format to guarantee flawless data structure generation without formatting errors.
- **Local Persistence:** Embedded SQLite database to automatically save, history-track, and instantly reload your generated personas.
- **Export to Markdown:** One-click export generates clean `.md` documentation ready to be shared or pasted into Notion/Obsidian.
- **Secure Key Management:** In-app encrypted credential settings that store your API key locally in an isolated configuration file.

---

## 🛠️ Architecture Overview

```text
buyer-persona-generator/
│
├── app.py              # Main Application File (UI Layout, Database & Threading)
├── requirements.txt    # Application Package Dependencies
├── .gitignore          # Keeps secrets and local database off GitHub
└── README.md           # Repository Documentation
```

### Generated Files (Excluded via `.gitignore`)
- `config.json`: Stores your local OpenAI API configuration key.
- `personas.db`: Single-file local SQLite database containing history logs.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9** or higher installed on your system.
- An active **OpenAI API Key** with access to `gpt-4o-mini`.

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com
   cd YOUR_REPO_NAME
   ```

2. **Create a Virtual Environment (Recommended)**
   - **Linux/macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. **Install Package Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Usage

1. **Launch the Desktop Application**
   ```bash
   python app.py
   ```

2. **Configure Authentication**
   - Click the **⚙️ API Settings** button in the top right corner.
   - Paste your OpenAI API key and save. The indicator will switch to green: `🟢 API Credential Active`.

3. **Generate Personas**
   - Fill out your Product profile, Target Market, and Core Customer Pain Point.
   - Click **🚀 Construct Buyer Persona**.
   - Review your persona instantly inside the Markdown reader.
   - Click **💾 Export markdown (.md)** to save a shareable copy to your local drive.

4. **Browse History**
   - Click any item on the left sidebar (**Saved Personas**) to instantly retrieve previously generated profiles from your local SQLite cache.

---

## 🔒 Security Best Practices

Your API Key is your responsibility. This project contains a pre-configured `.gitignore` file that ensures your `config.json` and local database (`personas.db`) are never pushed to public repositories.

**Never hardcode your API Key directly inside `app.py`.**

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
