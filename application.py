import tkinter as tk
from tkinter import scrolledtext, ttk
import serial
import serial.tools.list_ports
import threading
import queue

class ArduinoMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Solar Tracker - Live Serial Monitor")
        self.root.geometry("750x500")
        self.root.minsize(600, 400)

        self.serial_connection = None
        self.is_connected = False
        self.data_queue = queue.Queue()

        self.create_widgets()
        
        # Periodically check the queue for new serial data
        self.root.after(100, self.process_queue)

    def create_widgets(self,):
        # Top Control Panel Frame
        control_frame = ttk.LabelFrame(self.root, text=" Connection Settings ", padding=10)
        control_frame.pack(fill="x", padx=10, pady=10)

        # Port Selection
        ttk.Label(control_frame, text="Port:").pack(side="left", padx=5)
        self.port_combo = ttk.Combobox(control_frame, width=15, state="readonly")
        self.port_combo.pack(side="left", padx=5)
        self.refresh_ports()

        # Refresh Ports Button
        refresh_btn = ttk.Button(control_frame, text="Refresh", command=self.refresh_ports)
        refresh_btn.pack(side="left", padx=5)

        # Baud Rate Selection
        ttk.Label(control_frame, text="Baud:").pack(side="left", padx=5)
        self.baud_combo = ttk.Combobox(control_frame, width=10, values=["9600", "115200"], state="readonly")
        self.baud_combo.set("9600")
        self.baud_combo.pack(side="left", padx=5)

        # Connect / Disconnect Button
        self.connect_btn = ttk.Button(control_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=15)

        # Status Indicator
        self.status_label = ttk.Label(control_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(side="right", padx=5)

        # Live values reported by single_axis/single_axis.ino
        telemetry_frame = ttk.LabelFrame(self.root, text=" Live Tracker Data ", padding=10)
        telemetry_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.telemetry_values = {}
        telemetry_fields = (
            ("Left LDR", "N/A"),
            ("Right LDR", "N/A"),
            ("Difference", "N/A"),
            ("Tracking", "Waiting for data"),
            ("Rotation", "N/A"),
            ("Tilt", "N/A"),
        )
        for column, (name, initial_value) in enumerate(telemetry_fields):
            field_frame = ttk.Frame(telemetry_frame)
            field_frame.grid(row=0, column=column, padx=8, sticky="w")
            ttk.Label(field_frame, text=name).pack(anchor="w")
            value_label = ttk.Label(field_frame, text=initial_value, font=("TkDefaultFont", 11, "bold"))
            value_label.pack(anchor="w")
            self.telemetry_values[name] = value_label

        # Terminal / Log Area Frame
        terminal_frame = ttk.LabelFrame(self.root, text=" Live Arduino Output ", padding=10)
        terminal_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Scrolled Text Box (Acts as the terminal)
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame, 
            wrap=tk.WORD, 
            bg="#1e1e1e", 
            fg="#00ff66", 
            insertbackground="white",
            font=("Consolas", 10)
        )
        self.terminal.pack(fill="both", expand=True)
        
        # Clear Button
        clear_btn = ttk.Button(terminal_frame, text="Clear Terminal", command=self.clear_terminal)
        clear_btn.pack(anchor="e", pady=(5, 0))

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])
        else:
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
                self.status_label.config(text="Status: Connected", foreground="green")
                self.log_to_terminal(f"--- Connected to {port} at {baud} baud ---\n")

                # Start background reading thread
                self.thread = threading.Thread(target=self.read_serial, daemon=True)
                self.thread.start()
            except Exception as e:
                self.log_to_terminal(f"Connection Error: {e}\n")
        else:
            self.disconnect()

    def disconnect(self):
        self.is_connected = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connect_btn.config(text="Connect")
        self.status_label.config(text="Status: Disconnected", foreground="red")
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
            self.terminal.insert(tk.END, line + "\n")
            self.terminal.see(tk.END)
            self.update_telemetry(line)
        self.root.after(100, self.process_queue)

    def update_telemetry(self, line):
        fields = {}
        for part in line.split("|"):
            key, separator, value = part.strip().partition(":")
            if separator:
                fields[key.strip()] = value.strip()

        required_fields = ("Left LDR", "Right LDR", "Difference", "Rotation angle", "Tilt angle")
        if not all(field in fields for field in required_fields):
            return

        self.telemetry_values["Left LDR"].config(text=fields["Left LDR"])
        self.telemetry_values["Right LDR"].config(text=fields["Right LDR"])
        self.telemetry_values["Difference"].config(text=fields["Difference"])
        self.telemetry_values["Rotation"].config(text=fields["Rotation angle"])
        self.telemetry_values["Tilt"].config(text=fields["Tilt angle"])

        status = next(
            (part.strip() for part in line.split("|") if ":" not in part),
            "Unknown",
        )
        self.telemetry_values["Tracking"].config(text=status)

    def log_to_terminal(self, message):
        self.terminal.insert(tk.END, message)
        self.terminal.see(tk.END)

    def clear_terminal(self):
        self.terminal.delete('1.0', tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ArduinoMonitorApp(root)
    root.mainloop()