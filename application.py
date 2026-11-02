import tkinter as tk
from tkinter import scrolledtext, ttk
import re
import serial
import serial.tools.list_ports
import threading
import queue


class ArduinoMonitorApp:
    SOLAR_READING_PATTERN = re.compile(
        r"Pin A0 Voltage:\s*([\d.]+)\s*V.*?"
        r"Solar Panel Total:\s*([\d.]+)\s*V",
        re.IGNORECASE,
    )
    TRACKER_READING_PATTERN = re.compile(
        r"\bL:\s*(\d+)\s*\|\s*R:\s*(\d+)\s*\|\s*Diff:\s*(\d+)"
        r"\s*\|\s*Pos:\s*(\d+)\s*\|\s*State:\s*(.+)$",
        re.IGNORECASE,
    )
    TELEMETRY_KEYS = {"LDR_L", "LDR_R", "DIFF", "POS", "STATE", "VPIN", "VIN"}

    def __init__(self, root):
        self.root = root
        self.root.title("Solar Tracker Dashboard")
        self.root.geometry("1050x780")
        self.root.minsize(780, 650)
        self.root.configure(bg="#0b1220")

        self.serial_connection = None
        self.is_connected = False
        self.data_queue = queue.Queue()
        self.metric_labels = {}
        self.solar_pin_voltage = None
        self.solar_panel_voltage = None

        self.create_widgets()
        self.root.after(100, self.process_queue)

    def create_widgets(self):
        style = ttk.Style()
        style.configure(
            "Dashboard.TCombobox",
            fieldbackground="#111c2f",
            background="#111c2f",
            foreground="#e5edf8",
            arrowcolor="#a9b8cc",
            padding=6,
        )
        style.map(
            "Dashboard.TCombobox",
            fieldbackground=[("readonly", "#111c2f")],
            foreground=[("readonly", "#e5edf8")],
        )

        page = tk.Frame(self.root, bg="#0b1220")
        page.pack(fill="both", expand=True, padx=24, pady=20)

        header = tk.Frame(page, bg="#0b1220")
        header.pack(fill="x", pady=(0, 18))
        tk.Label(
            header,
            text="SOLAR TRACKER",
            bg="#0b1220",
            fg="#f4f7fb",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Live sensor readings and tracking position",
            bg="#0b1220",
            fg="#91a2ba",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        control_frame = tk.Frame(page, bg="#131e30", padx=16, pady=14)
        control_frame.pack(fill="x", pady=(0, 18))
        tk.Label(
            control_frame,
            text="DEVICE CONNECTION",
            bg="#131e30",
            fg="#91a2ba",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 14))

        self.port_combo = ttk.Combobox(
            control_frame, width=12, state="readonly", style="Dashboard.TCombobox"
        )
        self.port_combo.pack(side="left", padx=(0, 8))
        self.refresh_ports()
        ttk.Button(
            control_frame, text="Refresh", command=self.refresh_ports
        ).pack(side="left", padx=(0, 16))

        tk.Label(
            control_frame,
            text="BAUD",
            bg="#131e30",
            fg="#91a2ba",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 7))
        self.baud_combo = ttk.Combobox(
            control_frame,
            width=9,
            values=["9600", "115200"],
            state="readonly",
            style="Dashboard.TCombobox",
        )
        self.baud_combo.set("9600")
        self.baud_combo.pack(side="left", padx=(0, 14))

        # Connect / Disconnect Button
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=15)

        # Status Indicator
        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side="right", padx=5)

        metrics_frame = tk.Frame(page, bg="#0b1220")
        metrics_frame.pack(fill="x", pady=(0, 18))
        for column in range(3):
            metrics_frame.columnconfigure(column, weight=1)

        metric_cards = (
            ("LDR_L", "LDR LEFT", "0", "ADC", "#4ade80"),
            ("LDR_R", "LDR RIGHT", "0", "ADC", "#4ade80"),
            ("DIFF", "LDR DIFFERENCE", "0", "ADC", "#fbbf24"),
            ("VPIN", "PIN VOLTAGE", "--", "V", "#60a5fa"),
            ("VIN", "SOLAR INPUT", "--", "V", "#4ade80"),
            ("POS", "SERVO POSITION", "90°", "STABLE", "#f472b6"),
        )
        for index, (key, title, value, unit, color) in enumerate(metric_cards):
            self.metric_labels[key] = self.create_metric_card(
                metrics_frame, title, value, unit, color,
                row=index // 3, column=index % 3,
            )

        self.solar_update_label = tk.Label(
            page,
            text="Waiting for sensor readings",
            bg="#0b1220",
            fg="#91a2ba",
            font=("Segoe UI", 9),
        )
        self.solar_update_label.pack(anchor="w", pady=(0, 10))

        # Terminal / Log Area Frame
        terminal_frame = ttk.LabelFrame(page, text=" Live Arduino Output ", padding=10)
        terminal_frame.pack(fill="both", expand=True)

        # Scrolled Text Box (Acts as the terminal)
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            height=8,
            wrap=tk.WORD,
            bg="#0b1220",
            fg="#b9f6ca",
            insertbackground="white",
            font=("Consolas", 10),
            relief="flat",
            padx=10,
            pady=8,
        )
        self.terminal.pack(fill="both", expand=True)

    def create_metric_card(self, parent, title, value, unit, color, row, column):
        card = tk.Frame(
            parent,
            bg="#131e30",
            highlightbackground="#26354b",
            highlightthickness=1,
        )
        card.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")
        tk.Label(
            card,
            text=title,
            bg="#131e30",
            fg="#91a2ba",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 0))
        value_label = tk.Label(
            card,
            text=value,
            bg="#131e30",
            fg=color,
            font=("Segoe UI", 22, "bold"),
        )
        value_label.pack(anchor="center", expand=True, pady=(3, 0))
        unit_label = tk.Label(
            card,
            text=unit,
            bg="#131e30",
            fg="#91a2ba",
            font=("Segoe UI", 9),
        )
        unit_label.pack(anchor="e", padx=12, pady=(0, 8))
        return {"value": value_label, "unit": unit_label}

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports and self.port_combo.get() not in ports:
            self.port_combo.set(ports[0])
        elif not ports:
            self.port_combo.set('')

    def toggle_connection(self):
        if not self.is_connected:
            port = self.port_combo.get()
            baud = self.baud_combo.get()
            if not port:
                self.log_to_terminal("Error: No serial port selected!\n")
                return
            try:
                self.serial_connection = serial.Serial(port, int(baud), timeout=1)
                self.is_connected = True
                self.connect_btn.config(text="Disconnect")
                self.status_label.config(text="●  CONNECTED", fg="#4ade80")
                self.log_to_terminal(f"--- Connected to {port} at {baud} baud ---\n")

                self.thread = threading.Thread(target=self.read_serial, daemon=True)
                self.thread.start()
            except (serial.SerialException, PermissionError) as e:
                self.status_label.config(text="●  DISCONNECTED", fg="#fb7185")
                self.log_to_terminal(
                    f"Connection Error: {e}\n"
                    f"Check that {port} is not open in Arduino IDE Serial Monitor/Plotter "
                    "or another serial application, then refresh the port list and try again.\n"
                )
        else:
            self.disconnect()

    def disconnect(self):
        self.is_connected = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connect_btn.config(text="Connect")
        self.status_label.config(text="●  DISCONNECTED", fg="#fb7185")
        self.log_to_terminal("--- Disconnected from device ---\n")

    def read_serial(self):
        while self.is_connected:
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.data_queue.put(line)
            except Exception:
                break

    def process_queue(self):
        while not self.data_queue.empty():
            line = self.data_queue.get()
            self.update_metrics(line)
            self.terminal.insert(tk.END, line + "\n")
            self.terminal.see(tk.END) # Auto-scroll to the bottom
        self.root.after(100, self.process_queue)

    def update_metrics(self, line):
        tracker_match = self.TRACKER_READING_PATTERN.search(line)
        if tracker_match:
            data = {
                "LDR_L": tracker_match.group(1),
                "LDR_R": tracker_match.group(2),
                "DIFF": tracker_match.group(3),
                "POS": tracker_match.group(4),
                "STATE": tracker_match.group(5).strip(),
            }
        else:
            data = self.parse_telemetry_line(line)

        if data:
            self.update_metric_cards(data)
            self.solar_update_label.config(text="Live sensor reading received")

        match = self.SOLAR_READING_PATTERN.search(line)
        if match:
            self.solar_pin_voltage = float(match.group(1))
            self.solar_panel_voltage = float(match.group(2))
            self.update_metric_cards({
                "VPIN": str(self.solar_pin_voltage),
                "VIN": str(self.solar_panel_voltage),
            })
            self.solar_update_label.config(text="Live solar reading received")

    @classmethod
    def parse_telemetry_line(cls, line):
        data = {}
        for pair in line.split(","):
            key, separator, value = pair.partition(":")
            key = key.strip().upper()
            if separator and key in cls.TELEMETRY_KEYS and value.strip():
                data[key] = value.strip()
        return data

    def update_metric_cards(self, data):
        for key in ("LDR_L", "LDR_R", "DIFF"):
            if key in data:
                try:
                    value = f"{float(data[key]):g}"
                except ValueError:
                    continue
                self.metric_labels[key]["value"].config(text=value)

        for key in ("VPIN", "VIN"):
            if key in data:
                try:
                    value = f"{float(data[key]):.2f}"
                except ValueError:
                    continue
                self.metric_labels[key]["value"].config(text=value)

        if "POS" in data:
            try:
                position = f"{float(data['POS']):g}°"
            except ValueError:
                position = None
            if position is not None:
                self.metric_labels["POS"]["value"].config(text=position)
        if "STATE" in data:
            self.metric_labels["POS"]["unit"].config(text=data["STATE"])

    def log_to_terminal(self, message):
        self.terminal.insert(tk.END, message)
        self.terminal.see(tk.END)

    def clear_terminal(self):
        self.terminal.delete('1.0', tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoMonitorApp(root)
    root.mainloop()