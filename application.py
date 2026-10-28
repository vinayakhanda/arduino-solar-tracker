import tkinter as tk
from tkinter import scrolledtext, ttk
import re
import serial
import serial.tools.list_ports
import threading
import queue


class ArduinoMonitorApp:
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

        self.connect_btn = ttk.Button(
            control_frame, text="Connect", command=self.toggle_connection
        )
        self.connect_btn.pack(side="left")

        self.status_label = tk.Label(
            control_frame,
            text="●  DISCONNECTED",
            bg="#131e30",
            fg="#fb7185",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(side="right", padx=(10, 0))

        metrics = tk.Frame(page, bg="#0b1220")
        metrics.pack(fill="x", pady=(0, 18))
        for column in range(3):
            metrics.grid_columnconfigure(column, weight=1, uniform="metric")

        cards = [
            ("LEFT LDR", "left", "Raw sensor reading", "#38bdf8"),
            ("RIGHT LDR", "right", "Raw sensor reading", "#a78bfa"),
            ("LIGHT DIFFERENCE", "difference", "Left minus right", "#fbbf24"),
            ("ROTATION", "rotation", "Servo position · degrees", "#34d399"),
            ("TILT", "tilt", "Servo position · degrees", "#2dd4bf"),
            ("TRACKING MODE", "mode", "Current tracker state", "#fb923c"),
        ]
        for index, (title, key, detail, accent) in enumerate(cards):
            card = tk.Frame(metrics, bg="#131e30", padx=16, pady=14)
            card.grid(
                row=index // 3,
                column=index % 3,
                sticky="nsew",
                padx=(0 if index % 3 == 0 else 6, 6 if index % 3 < 2 else 0),
                pady=(0, 12) if index < 3 else (0, 0),
            )
            tk.Label(
                card,
                text=title,
                bg="#131e30",
                fg=accent,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w")
            value = tk.Label(
                card,
                text="--" if key != "mode" else "WAITING",
                bg="#131e30",
                fg="#f4f7fb",
                font=("Segoe UI", 22 if key != "mode" else 16, "bold"),
                anchor="w",
            )
            value.pack(anchor="w", pady=(9, 2))
            tk.Label(
                card,
                text=detail,
                bg="#131e30",
                fg="#91a2ba",
                font=("Segoe UI", 9),
            ).pack(anchor="w")
            self.metric_labels[key] = value

        terminal_frame = tk.Frame(page, bg="#131e30", padx=14, pady=12)
        terminal_frame.pack(fill="both", expand=True)
        terminal_header = tk.Frame(terminal_frame, bg="#131e30")
        terminal_header.pack(fill="x", pady=(0, 9))
        tk.Label(
            terminal_header,
            text="LIVE ARDUINO OUTPUT",
            bg="#131e30",
            fg="#e5edf8",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        ttk.Button(
            terminal_header, text="Clear", command=self.clear_terminal
        ).pack(side="right")

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
            self.terminal.see(tk.END)
        self.root.after(100, self.process_queue)

    def update_metrics(self, line):
        values = {
            "left": r"Left LDR:\s*(-?\d+)",
            "right": r"Right LDR:\s*(-?\d+)",
            "difference": r"Difference:\s*(-?\d+)",
            "rotation": r"Rotation angle:\s*(-?\d+)",
            "tilt": r"Tilt angle:\s*(-?\d+)",
        }
        for key, pattern in values.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                self.metric_labels[key].config(text=match.group(1))

        mode = re.search(
            r"\b(NIGHT - CENTRED|EQUAL LIGHT - CENTRED|TRACKING LEFT|TRACKING RIGHT)\b",
            line,
            re.IGNORECASE,
        )
        if mode:
            self.metric_labels["mode"].config(text=mode.group(1).upper())

    def log_to_terminal(self, message):
        self.terminal.insert(tk.END, message)
        self.terminal.see(tk.END)

    def clear_terminal(self):
        self.terminal.delete('1.0', tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoMonitorApp(root)
    root.mainloop()