import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading
import queue
import time
import re
from datetime import datetime


class SolarTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Solar Tracker & Voltage Dashboard")
        self.geometry("840x730")
        self.configure(bg="#1E1E2E")
        self.resizable(True, True)

        self.ser = None
        self.data_queue = queue.Queue()
        self.running = False

        self.create_widgets()
        self.process_queue()

    def create_widgets(self):
        # Header
        header = tk.Label(
            self,
            text="SOLAR TRACKER MONITORING DASHBOARD",
            font=("Helvetica", 16, "bold"),
            bg="#1E1E2E",
            fg="#89B4FA"
        )
        header.pack(pady=(15, 5))

        # Port Selection Bar
        port_frame = tk.Frame(self, bg="#1E1E2E")
        port_frame.pack(pady=5)

        tk.Label(
            port_frame, text="Select Port:", font=("Helvetica", 10), bg="#1E1E2E", fg="#CDD6F4"
        ).pack(side="left", padx=5)

        self.port_combobox = ttk.Combobox(port_frame, state="readonly", width=18)
        self.port_combobox.pack(side="left", padx=5)
        self.refresh_ports()

        self.btn_refresh = tk.Button(
            port_frame,
            text="Refresh",
            command=self.refresh_ports,
            bg="#45475A",
            fg="white",
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2"
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_connect = tk.Button(
            port_frame,
            text="Connect",
            command=self.toggle_connection,
            bg="#A6E3A1",
            fg="#11111B",
            font=("Helvetica", 9, "bold"),
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2"
        )
        self.btn_connect.pack(side="left", padx=5)

        # Connection Status
        self.status_label = tk.Label(
            self,
            text="Status: Disconnected",
            font=("Helvetica", 10, "italic"),
            bg="#1E1E2E",
            fg="#F9E2AF"
        )
        self.status_label.pack(pady=(5, 10))

        # Metric Cards Container
        cards_frame = tk.Frame(self, bg="#1E1E2E")
        cards_frame.pack(padx=20, pady=5, fill="x")

        cards_frame.columnconfigure((0, 1, 2), weight=1)
        cards_frame.rowconfigure((0, 1), weight=1)

        # Visual Dashboard Cards
        self.card_ldr_l = self.create_card(cards_frame, "LDR Left", "0", "Units", "#A6E3A1", 0, 0)
        self.card_ldr_r = self.create_card(cards_frame, "LDR Right", "0", "Units", "#A6E3A1", 0, 1)
        self.card_diff = self.create_card(cards_frame, "LDR Diff", "0", "Delta", "#FAB387", 0, 2)
        self.card_vpin = self.create_card(cards_frame, "Pin A5 Voltage", "0.00", "V", "#89B4FA", 1, 0)
        self.card_vin = self.create_card(cards_frame, "Solar Input (V_In)", "0.00", "V", "#F9E2AF", 1, 1)
        self.card_servo = self.create_card(cards_frame, "Servo Position", "90°", "STABLE", "#F5C2E7", 1, 2)

        # Serial Terminal Log Widget
        terminal_frame = tk.Frame(self, bg="#181825", highlightbackground="#45475A", highlightthickness=1)
        terminal_frame.pack(padx=20, pady=(15, 20), fill="both", expand=True)

        terminal_header = tk.Label(
            terminal_frame,
            text=" SERIAL TERMINAL LOG",
            font=("Consolas", 10, "bold"),
            bg="#181825",
            fg="#CDD6F4",
            anchor="w"
        )
        terminal_header.pack(fill="x", padx=10, pady=(6, 2))

        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            wrap=tk.WORD,
            bg="#11111B",
            fg="#A6E3A1",
            insertbackground="white",
            font=("Consolas", 9),
            height=8
        )
        self.terminal.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        self.log_to_terminal("System initialized. Select a port and click Connect.")

    def create_card(self, parent, title, val, unit, color, row, col):
        frame = tk.Frame(parent, bg="#313244", highlightbackground=color, highlightthickness=2, bd=0)
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        lbl_title = tk.Label(frame, text=title.upper(), font=("Helvetica", 9, "bold"), bg="#313244", fg="#CDD6F4")
        lbl_title.pack(anchor="w", padx=10, pady=(10, 0))

        lbl_val = tk.Label(frame, text=val, font=("Helvetica", 20, "bold"), bg="#313244", fg=color)
        lbl_val.pack(anchor="center", expand=True)

        lbl_unit = tk.Label(frame, text=unit, font=("Helvetica", 8), bg="#313244", fg="#A6ADC8")
        lbl_unit.pack(anchor="e", padx=10, pady=(0, 8))

        return {"value": lbl_val, "unit": lbl_unit}

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports:
            self.port_combobox.current(0)
        else:
            self.port_combobox.set('')

    def toggle_connection(self):
        if self.running:
            self.running = False
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.btn_connect.config(text="Connect", bg="#A6E3A1", fg="#11111B")
            self.status_label.config(text="Status: Disconnected")
            self.log_to_terminal("Disconnected from serial port.")
        else:
            selected_port = self.port_combobox.get()
            if not selected_port:
                self.log_to_terminal("ERROR: No serial port selected.")
                return

            self.running = True
            self.thread = threading.Thread(target=self.read_serial, args=(selected_port,), daemon=True)
            self.thread.start()

    def read_serial(self, port):
        try:
            self.ser = serial.Serial(port, 9600, timeout=1)
            time.sleep(1.5)  # Allow Arduino reset buffer to clear
            self.data_queue.put(("STATUS", f"Connected to {port}"))
            self.data_queue.put(("LOG", f"Connected successfully to {port}"))
            self.data_queue.put(("BTN_STATE", "Disconnect"))

            while self.running:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.data_queue.put(("LOG", f"RX: {line}"))
                        parsed_data = self.parse_serial_line(line)
                        if parsed_data:
                            self.data_queue.put(("DATA", parsed_data))
                time.sleep(0.01)
        except serial.SerialException as e:
            self.running = False
            self.data_queue.put(("STATUS", "Connection Failed"))
            self.data_queue.put(("LOG", f"ERROR: Could not open {port}. {e}"))
            self.data_queue.put(("BTN_STATE", "Connect"))

    def parse_serial_line(self, line):
        data_dict = {}

        # 1. Parse Key-Value structure: "LDR_L:500,LDR_R:480,DIFF:20,POS:90..."
        if ":" in line and "," in line:
            try:
                pairs = line.split(',')
                for pair in pairs:
                    if ':' in pair:
                        k, v = pair.split(':', 1)
                        data_dict[k.strip()] = v.strip()
                return data_dict
            except Exception:
                pass

        # 2. Fallback parser for pipe format: "L: 500 | R: 480 | Diff: 20 | Pos: 90 | State: STABLE"
        if "|" in line:
            try:
                parts = line.split("|")
                for part in parts:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        k, v = k.strip(), v.strip()
                        if k == "L": data_dict["LDR_L"] = v
                        elif k == "R": data_dict["LDR_R"] = v
                        elif k == "Diff": data_dict["DIFF"] = v
                        elif k == "Pos": data_dict["POS"] = v
                        elif k == "State": data_dict["STATE"] = v
                return data_dict
            except Exception:
                pass

        # 3. Fallback parser for legacy voltage lines: "[VOLTAGE] Pin Voltage: 2.50 V | Input Voltage: 5.00 V"
        if "VOLTAGE" in line:
            vpin_match = re.search(r"Pin Voltage:\s*([0-9.]+)", line)
            vin_match = re.search(r"Input Voltage:\s*([0-9.]+)", line)
            if vpin_match:
                data_dict["VPIN"] = vpin_match.group(1)
            if vin_match:
                data_dict["VIN"] = vin_match.group(1)
            return data_dict if data_dict else None

        return None

    def process_queue(self):
        try:
            while not self.data_queue.empty():
                msg_type, payload = self.data_queue.get_nowait()
                if msg_type == "STATUS":
                    self.status_label.config(text=f"Status: {payload}")
                elif msg_type == "LOG":
                    self.log_to_terminal(payload)
                elif msg_type == "DATA":
                    self.update_cards(payload)
                elif msg_type == "BTN_STATE":
                    if payload == "Disconnect":
                        self.btn_connect.config(text="Disconnect", bg="#F38BA8", fg="#11111B")
                    else:
                        self.btn_connect.config(text="Connect", bg="#A6E3A1", fg="#11111B")
        except queue.Empty:
            pass

        self.after(50, self.process_queue)

    def update_cards(self, data):
        if "LDR_L" in data:
            self.card_ldr_l["value"].config(text=data["LDR_L"])
        if "LDR_R" in data:
            self.card_ldr_r["value"].config(text=data["LDR_R"])
        if "DIFF" in data:
            self.card_diff["value"].config(text=data["DIFF"])
        if "VPIN" in data:
            try:
                self.card_vpin["value"].config(text=f"{float(data['VPIN']):.2f}")
            except ValueError:
                pass
        if "VIN" in data:
            try:
                self.card_vin["value"].config(text=f"{float(data['VIN']):.2f}")
            except ValueError:
                pass
        if "POS" in data:
            self.card_servo["value"].config(text=f"{data['POS']}°")
        if "STATE" in data:
            self.card_servo["unit"].config(text=data["STATE"])

    def log_to_terminal(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {message}\n")
        self.terminal.see(tk.END)

    def on_closing(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.destroy()


if __name__ == "__main__":
    app = SolarTrackerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()