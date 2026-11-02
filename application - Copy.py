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

        solar_frame = tk.LabelFrame(
            page,
            text=" SOLAR OUTPUT ",
            bg="#131e30",
            fg="#91a2ba",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=12,
            relief="flat",
        )
        solar_frame.pack(fill="x", pady=(0, 18))

        solar_values = tk.Frame(solar_frame, bg="#131e30")
        solar_values.pack(fill="x")
        self.pin_voltage_label = tk.Label(
            solar_values,
            text="A0 input: -- V",
            bg="#131e30",
            fg="#e5edf8",
            font=("Segoe UI", 13, "bold"),
        )
        self.pin_voltage_label.pack(side="left", padx=(0, 36))
        self.panel_voltage_label = tk.Label(
            solar_values,
            text="Solar panel: -- V",
            bg="#131e30",
            fg="#4ade80",
            font=("Segoe UI", 13, "bold"),
        )
        self.panel_voltage_label.pack(side="left")
        self.solar_update_label = tk.Label(
            solar_frame,
            text="Waiting for solar readings",
            bg="#131e30",
            fg="#91a2ba",
            font=("Segoe UI", 9),
        )
        self.solar_update_label.pack(anchor="w", pady=(6, 0))

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
        match = self.SOLAR_READING_PATTERN.search(line)
        if not match:
            return

        self.solar_pin_voltage = float(match.group(1))
        self.solar_panel_voltage = float(match.group(2))
        self.pin_voltage_label.config(text=f"A0 input: {self.solar_pin_voltage:.2f} V")
        self.panel_voltage_label.config(
            text=f"Solar panel: {self.solar_panel_voltage:.2f} V"
        )
        self.solar_update_label.config(text="Live solar reading received")

    def log_to_terminal(self, message):
        self.terminal.insert(tk.END, message)
        self.terminal.see(tk.END)

    def clear_terminal(self):
        self.terminal.delete('1.0', tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoMonitorApp(root)
    root.mainloop()