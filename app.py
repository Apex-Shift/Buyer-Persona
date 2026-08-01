import json
import os
import sqlite3
import sys
from openai import OpenAI
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

CONFIG_FILE = "config.json"
DB_FILE = "personas.db"


class DatabaseManager:
    """Handles local storage using SQLite."""

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.create_table()

    def create_table(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS personas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    product TEXT,
                    target TEXT,
                    json_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def save_persona(self, name, product, target, json_data):
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO personas (name, product, target, json_data) VALUES (?, ?, ?, ?)",
                (name, product, target, json_data),
            )
            return cursor.lastrowid

    def get_all_personas(self):
        cursor = self.conn.execute(
            "SELECT id, name, product FROM personas ORDER BY id DESC"
        )
        return cursor.fetchall()

    def get_persona_details(self, persona_id):
        cursor = self.conn.execute(
            "SELECT json_data FROM personas WHERE id = ?", (persona_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else None


class PersonaWorker(QThread):
    """Asynchronous worker to handle JSON-structured OpenAI API calls."""

    success = Signal(str)
    error = Signal(str)

    def __init__(self, api_key, product, target, pain_point):
        super().__init__()
        self.api_key = api_key
        self.product = product
        self.target = target
        self.pain_point = pain_point

    def run(self):
        try:
            client = OpenAI(api_key=self.api_key)

            # JSON Schema enforcement for structured output
            json_schema = {
                "name": "buyer_persona",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "job_title": {"type": "string"},
                        "income": {"type": "string"},
                        "family_status": {"type": "string"},
                        "biography": {"type": "string"},
                        "goals": {"type": "array", "items": {"type": "string"}},
                        "frustrations": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "product_alignment": {"type": "string"},
                        "marketing_channels": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "name",
                        "age",
                        "job_title",
                        "income",
                        "family_status",
                        "biography",
                        "goals",
                        "frustrations",
                        "product_alignment",
                        "marketing_channels",
                    ],
                    "additionalProperties": False,
                },
            }

            prompt = f"""
            Act as an expert marketing strategist. Create a realistic and highly detailed buyer persona based on:
            - Product: {self.product}
            - Target Audience: {self.target}
            - Main Pain Point: {self.pain_point}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise marketing tool that generates structured buyer personas.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": json_schema,
                },
                temperature=0.7,
            )

            self.success.emit(response.choices.message.content)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buyer Persona ")
        self.resize(1000, 650)

        self.db = DatabaseManager()
        self.api_key = self.load_api_key()
        self.current_loaded_json = None

        self.init_ui()
        self.refresh_history_list()

    def init_ui(self):
        # Main layout structure using a horizontal splitter for history sidebar
        main_splitter = QSplitter()
        self.setCentralWidget(main_splitter)

        # ---- LEFT SIDEBAR: History Panel ----
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)

        sidebar_layout.addWidget(QLabel("<b>Saved Personas</b>"))
        self.history_list = QListWidget()
        self.history_list.currentRowChanged.connect(self.load_selected_persona)
        sidebar_layout.addWidget(self.history_list)

        main_splitter.addWidget(sidebar_widget)

        # ---- RIGHT PANEL: Workspace ----
        workspace_widget = QWidget()
        workspace_layout = QVBoxLayout(workspace_widget)
        main_splitter.addWidget(workspace_widget)

        # Top Control & API Bar
        top_bar = QHBoxLayout()
        self.status_label = QLabel()
        self.update_status_label()
        self.btn_config = QPushButton("⚙️ API Settings")
        self.btn_config.clicked.connect(self.open_config_dialog)
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_config)
        workspace_layout.addLayout(top_bar)

        # Inputs Form
        form_layout = QFormLayout()
        self.input_product = QLineEdit()
        self.input_product.setPlaceholderText("e.g., Notion for real estate agents")
        self.input_target = QLineEdit()
        self.input_target.setPlaceholderText("e.g., Independent Realtors")
        self.input_pain = QLineEdit()
        self.input_pain.setPlaceholderText(
            "e.g., Scattered client data and missed follow-ups"
        )

        form_layout.addRow("Your Product:", self.input_product)
        form_layout.addRow("Target Market:", self.input_target)
        form_layout.addRow("Core Pain Point:", self.input_pain)
        workspace_layout.addLayout(form_layout)

        # Process Button
        self.btn_generate = QPushButton("🚀 Construct Buyer Persona")
        self.btn_generate.setStyleSheet(
            "font-weight: bold; padding: 10px; background-color: #007acc; color: white; border-radius: 4px;"
        )
        self.btn_generate.clicked.connect(self.start_generation)
        workspace_layout.addWidget(self.btn_generate)

        # Display Area
        workspace_layout.addWidget(QLabel("<b>Persona Output Preview</b>"))
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        workspace_layout.addWidget(self.output_area)

        # Export Actions Panel
        actions_layout = QHBoxLayout()
        self.btn_export_md = QPushButton("💾 Export markdown (.md)")
        self.btn_export_md.setEnabled(False)
        self.btn_export_md.clicked.connect(self.export_to_markdown)
        actions_layout.addWidget(self.btn_export_md)

        workspace_layout.addLayout(actions_layout)

        # Set ratio rules for the splitter (25% sidebar, 75% workspace)
        main_splitter.setSizes([250, 750])

    # ---- API Credentials Handling ----
    def load_api_key(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f).get("api_key", "")
            except Exception:
                return ""
        return ""

    def save_api_key(self, key):
        self.api_key = key
        with open(CONFIG_FILE, "w") as f:
            json.dump({"api_key": key}, f)
        self.update_status_label()

    def update_status_label(self):
        if self.api_key:
            self.status_label.setText("🟢 API Credential Active")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("🔴 Missing OpenAI API Key")
            self.status_label.setStyleSheet("color: red;")

    @Slot()
    def open_config_dialog(self):
        key, ok = QInputDialog.getText(
            self,
            "API Authentication",
            "Paste your OpenAI API Key:",
            QLineEdit.EchoMode.Password,
            self.api_key,
        )
        if ok and key.strip():
            self.save_api_key(key.strip())

    # ---- Business Logic and Workers Handling ----
    @Slot()
    def start_generation(self):
        if not self.api_key:
            QMessageBox.warning(
                self, "Missing Key", "Please configure your API key first."
            )
            return

        product = self.input_product.text().strip()
        target = self.input_target.text().strip()
        pain = self.input_pain.text().strip()

        if not product or not target or not pain:
            QMessageBox.warning
        if not product or not target or not pain:
            QMessageBox.warning(
                self, "Required Fields", "Please populate all fields."
            )
            return

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Engaging Model Thread...")

        self.worker = PersonaWorker(self.api_key, product, target, pain)
        self.worker.success.connect(self.on_generation_success)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()

    @Slot(str)
    def on_generation_success(self, json_string):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 Construct Buyer Persona")

        try:
            parsed_data = json.loads(json_string)
            self.current_loaded_json = parsed_data

            # Database persistence
            product = self.input_product.text().strip()
            target = self.input_target.text().strip()
            self.db.save_persona(
                parsed_data["name"], product, target, json_string
            )

            # Update displays
            self.refresh_history_list()
            self.display_persona_dict(parsed_data)
            self.btn_export_md.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(
                self, "Data Error", f"Failed to parse target JSON: {str(e)}"
            )

    @Slot(str)
    def on_generation_error(self, error_message):
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("🚀 Construct Buyer Persona")
        QMessageBox.critical(self, "API Execution Failure", error_message)

    # ---- Data Formatting and Presentation ----
    def convert_json_to_markdown(self, data):
        """Helper to transform the database JSON payload into readable Markdown."""
        md = f"# Buyer Persona: {data['name']}\n\n"
        md += "## 👤 Demographics\n"
        md += f"- **Age**: {data['age']}\n"
        md += f"- **Job Title**: {data['job_title']}\n"
        md += f"- **Income**: {data['income']}\n"
        md += f"- **Family Status**: {data['family_status']}\n\n"
        md += f"## 📝 Biography\n{data['biography']}\n\n"

        md += "## 🎯 Goals & Targets\n"
        for goal in data["goals"]:
            md += f"- {goal}\n"

        md += "\n## ⚠️ Core Frustrations & Roadblocks\n"
        for frustration in data["frustrations"]:
            md += f"- {frustration}\n"

        md += f"\n## 🤝 Product Value Proposition Alignment\n{data['product_alignment']}\n\n"

        md += "## 🌐 Media & Communication Channels\n"
        for channel in data["marketing_channels"]:
            md += f"- {channel}\n"
        return md

    def display_persona_dict(self, data):
        markdown_content = self.convert_json_to_markdown(data)
        self.output_area.setMarkdown(markdown_content)

    # ---- Local History Operations ----
    def refresh_history_list(self):
        self.history_list.clear()
        self.records = self.db.get_all_personas()
        for record in self.records:
            # Displays: "John Doe (Product Name)" in the sidebar list
            self.history_list.addItem(f"{record[1]} ({record[2]})")

    @Slot(int)
    def load_selected_persona(self, row_index):
        if row_index < 0 or row_index >= len(self.records):
            return
        db_id = self.records[row_index][0]
        json_data_str = self.db.get_persona_details(db_id)

        if json_data_str:
            # Unwrap the tuple from sqlite fetchone
            self.current_loaded_json = json.loads(json_data_str[0])
            self.display_persona_dict(self.current_loaded_json)
            self.btn_export_md.setEnabled(True)

    # ---- Export Operations ----
    @Slot()
    def export_to_markdown(self):
        if not self.current_loaded_json:
            return

        filename = (
            f"persona_{self.current_loaded_json['name'].lower().replace(' ', '_')}.md"
        )
        try:
            markdown_text = self.convert_json_to_markdown(
                self.current_loaded_json
            )
            with open(filename, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            QMessageBox.information(
                self, "Export Successful", f"Saved profile to {filename}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Disk IO Error", f"Could not write file: {str(e)}"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
