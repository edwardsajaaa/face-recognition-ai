import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import face_recognition
import os
from datetime import datetime
import locale
import csv
from tkinter import messagebox
import openpyxl
from openpyxl.styles import Font

try:
    locale.setlocale(locale.LC_TIME, 'id_ID')
except locale.Error:
    print("Locale 'id_ID' tidak ditemukan. Menggunakan locale default.")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistem Absensi Wajah Cerdas (Full Fitur)")
        self.geometry("1000x800")
        self.resizable(False, False)

        # FUNGSI BARU: Deteksi kamera saat aplikasi dimulai
        self.available_cameras = self.detect_available_cameras()
        if not self.available_cameras:
            messagebox.showerror("Kamera Error", "Tidak ada kamera yang terdeteksi. Aplikasi akan ditutup.")
            self.destroy()
            return

        # Inisialisasi variabel
        self.registered_users = ["Pilih Nama..."]
        self.known_face_encodings = []
        self.known_face_names = []
        self.attendance_log = set()
        self.attendance_mode = False
        self.capture_mode = False
        self.capture_info_text = ""
        self.folder_path = 'gambar_kehadiran'

        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        self.load_known_faces()
        
        # Inisialisasi kamera dengan yang pertama kali ditemukan
        initial_camera_index = int(self.available_cameras[0].split(' ')[1])
        self.cap = cv2.VideoCapture(initial_camera_index)
        
        # Siapkan UI
        self.create_widgets()
        
        # Mulai loop
        self.update_frame()
        self.update_clock()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- FUNGSI BARU: Untuk mendeteksi semua kamera yang tersedia ---
    def detect_available_cameras(self):
        cameras = []
        # Cek hingga 5 indeks kamera, biasanya sudah lebih dari cukup
        for i in range(5):
            cap_test = cv2.VideoCapture(i)
            if cap_test.isOpened():
                cameras.append(f"Kamera {i}")
                cap_test.release()
        print(f"Kamera yang terdeteksi: {cameras}")
        return cameras

    # --- FUNGSI BARU: Untuk mengganti kamera saat dipilih dari dropdown ---
    def change_camera(self, selected_camera: str):
        try:
            new_camera_index = int(selected_camera.split(' ')[1])
            self.cap.release() # Lepaskan kamera yang sedang aktif
            self.cap = cv2.VideoCapture(new_camera_index) # Aktifkan kamera baru
            print(f"Berhasil beralih ke {selected_camera}")
        except Exception as e:
            messagebox.showerror("Error Ganti Kamera", f"Gagal beralih ke {selected_camera}.\nError: {e}")


    def create_widgets(self):
        # Struktur Frame Utama
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Frame Kiri (Video) ---
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(fill="both", expand=True)

        # --- Frame Kanan (Kontrol & Log) ---
        self.main_control_frame = ctk.CTkScrollableFrame(self, label_text="Panel Kontrol & Log")
        self.main_control_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        # --- WIDGET BARU: Pemilihan Kamera ---
        camera_frame = ctk.CTkFrame(self.main_control_frame)
        camera_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(camera_frame, text="Pilih Sumber Kamera", font=("Arial", 16, "bold")).pack()
        self.camera_menu = ctk.CTkOptionMenu(camera_frame, values=self.available_cameras, command=self.change_camera)
        self.camera_menu.pack(pady=10, padx=10, fill="x")

        # --- Jam Live ---
        self.clock_label = ctk.CTkLabel(self.main_control_frame, text="", font=("Arial", 16, "bold"))
        self.clock_label.pack(pady=10, fill="x")
        
        # ... (Sisa widget lainnya tetap sama) ...
        reg_frame = ctk.CTkFrame(self.main_control_frame)
        reg_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(reg_frame, text="Pendaftaran Wajah Baru", font=("Arial", 16, "bold")).pack(pady=5)
        self.name_entry = ctk.CTkEntry(reg_frame, placeholder_text="Masukkan nama (contoh: budi_s)")
        self.name_entry.pack(pady=10, padx=10, fill="x")
        self.save_button = ctk.CTkButton(reg_frame, text="Ambil 40 Sampel Wajah", command=self.save_face)
        self.save_button.pack(pady=10, padx=10, fill="x")

        att_frame = ctk.CTkFrame(self.main_control_frame)
        att_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(att_frame, text="Kontrol Absensi", font=("Arial", 16, "bold")).pack(pady=5)
        self.start_button = ctk.CTkButton(att_frame, text="Mulai Absensi", command=self.start_attendance, fg_color="green")
        self.start_button.pack(pady=10, padx=10, fill="x")
        self.stop_button = ctk.CTkButton(att_frame, text="Hentikan Absensi", command=self.stop_attendance, fg_color="red", state="disabled")
        self.stop_button.pack(pady=10, padx=10, fill="x")
        
        manual_frame = ctk.CTkFrame(self.main_control_frame)
        manual_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(manual_frame, text="Set Status Manual", font=("Arial", 16, "bold")).pack(pady=5)
        self.manual_name_menu = ctk.CTkOptionMenu(manual_frame, values=self.registered_users)
        self.manual_name_menu.pack(pady=10, padx=10, fill="x")
        self.manual_status_menu = ctk.CTkOptionMenu(manual_frame, values=["Izin", "Sakit"])
        self.manual_status_menu.pack(pady=5, padx=10, fill="x")
        self.set_status_button = ctk.CTkButton(manual_frame, text="Simpan Status", command=self.set_manual_status)
        self.set_status_button.pack(pady=10, padx=10, fill="x")
        
        export_frame = ctk.CTkFrame(self.main_control_frame)
        export_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(export_frame, text="Ekspor Laporan", font=("Arial", 16, "bold")).pack(pady=5)
        ctk.CTkLabel(export_frame, text="Tanggal Mulai:").pack(padx=10, anchor="w")
        self.start_date_entry = ctk.CTkEntry(export_frame, placeholder_text="YYYY-MM-DD")
        self.start_date_entry.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(export_frame, text="Tanggal Akhir:").pack(padx=10, anchor="w")
        self.end_date_entry = ctk.CTkEntry(export_frame, placeholder_text="YYYY-MM-DD")
        self.end_date_entry.pack(pady=5, padx=10, fill="x")
        self.export_button = ctk.CTkButton(export_frame, text="Ekspor ke Excel", command=self.export_to_excel)
        self.export_button.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(self.main_control_frame, text="Log Kehadiran Hari Ini", font=("Arial", 14, "bold")).pack(pady=(10,0))
        self.log_textbox = ctk.CTkTextbox(self.main_control_frame, state="disabled", font=("Arial", 12), height=200)
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)

    # ... (Semua fungsi lain dari export_to_excel hingga on_closing tetap sama persis seperti sebelumnya) ...
    # ... Saya akan copy-paste kembali agar Anda punya kode yang utuh ...
    def export_to_excel(self):
        start_date_str = self.start_date_entry.get()
        end_date_str = self.end_date_entry.get()
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            messagebox.showerror("Error Format Tanggal", "Format tanggal salah. Harap gunakan YYYY-MM-DD.")
            return
        filtered_data = []
        try:
            with open('kehadiran.csv', 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                filtered_data.append(header)
                for row in reader:
                    row_date = datetime.strptime(row[2], '%Y-%m-%d').date()
                    if start_date <= row_date <= end_date:
                        filtered_data.append(row)
        except FileNotFoundError:
            messagebox.showerror("Error File", "File kehadiran.csv tidak ditemukan.")
            return
        except Exception as e:
            messagebox.showerror("Error Membaca File", f"Terjadi error: {e}")
            return
        if len(filtered_data) <= 1:
            messagebox.showinfo("Info", "Tidak ada data kehadiran pada rentang tanggal tersebut.")
            return
        try:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Laporan Kehadiran"
            for row_data in filtered_data:
                sheet.append(row_data)
            bold_font = Font(bold=True)
            for cell in sheet["1:1"]:
                cell.font = bold_font
            for column_cells in sheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = length + 2
            filename = f"Laporan_Kehadiran_{start_date_str}_hingga_{end_date_str}.xlsx"
            workbook.save(filename)
            messagebox.showinfo("Ekspor Berhasil", f"Laporan berhasil diekspor ke file:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error Ekspor", f"Gagal mengekspor ke Excel: {e}")

    def load_known_faces(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.registered_users = ["Pilih Nama..."] + sorted(list(set(os.path.splitext(f)[0].rsplit('_', 1)[0] for f in os.listdir(self.folder_path))))
        if hasattr(self, 'manual_name_menu'):
            self.manual_name_menu.configure(values=self.registered_users)
        print(f"Memuat data wajah dari {len(self.registered_users)-1} orang...")
        for name in self.registered_users[1:]:
            try:
                image_path = os.path.join(self.folder_path, f"{name}_1.jpg")
                if os.path.exists(image_path):
                    face_image = face_recognition.load_image_file(image_path)
                    face_encoding = face_recognition.face_encodings(face_image)[0]
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(name)
            except IndexError:
                print(f"Peringatan: Tidak ada wajah terdeteksi di {name}_1.jpg.")
        print("Selesai.")

    def update_clock(self):
        now = datetime.now()
        clock_str = now.strftime("%A, %d %B %Y - %H:%M:%S") 
        self.clock_label.configure(text=clock_str)
        self.after(1000, self.update_clock)
        
    def update_frame(self):
        if not self.cap.isOpened():
             self.after(15, self.update_frame)
             return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            if self.capture_mode:
                cv2.putText(frame, self.capture_info_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)
            if self.attendance_mode:
                rgb_small_frame = cv2.cvtColor(cv2.resize(frame, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                for face_encoding, face_loc in zip(face_encodings, face_locations):
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
                    name = "Tidak Dikenal"
                    if True in matches:
                        first_match_index = matches.index(True)
                        name = self.known_face_names[first_match_index]
                        self.mark_attendance(name)
                    top, right, bottom, left = [coord * 4 for coord in face_loc]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name.upper(), (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.video_label.configure(image=img_tk)
        self.after(15, self.update_frame)

    def save_face(self):
        name = self.name_entry.get()
        if not name:
            messagebox.showerror("Error", "Nama tidak boleh kosong!")
            return
        self.save_button.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.set_status_button.configure(state="disabled")
        self.capture_mode = True
        self.capture_samples_loop(1, name)

    def capture_samples_loop(self, sample_num, name):
        if sample_num <= 40:
            self.capture_info_text = f"Mengambil gambar ke-{sample_num} dari 40"
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                filename = os.path.join(self.folder_path, f"{name}_{sample_num}.jpg")
                cv2.imwrite(filename, frame)
            self.after(200, lambda: self.capture_samples_loop(sample_num + 1, name))
        else:
            self.capture_info_text = "Pengambilan Sampel Selesai!"
            self.load_known_faces()
            self.name_entry.delete(0, 'end')
            self.after(2000, self.reset_capture_mode)

    def reset_capture_mode(self):
        self.capture_mode = False
        self.capture_info_text = ""
        self.save_button.configure(state="normal")
        self.start_button.configure(state="normal")
        self.set_status_button.configure(state="normal")

    def set_manual_status(self):
        name = self.manual_name_menu.get()
        status = self.manual_status_menu.get()
        if name == "Pilih Nama...":
            messagebox.showerror("Error", "Silakan pilih nama terlebih dahulu.")
            return
        self.log_entry(name, status)

    def log_entry(self, name, time_or_status):
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        log_entry_check = f"{name}-{today_str}"
        if log_entry_check not in self.attendance_log:
            self.attendance_log.add(log_entry_check)
            day_name_str = now.strftime('%A')
            with open('kehadiran.csv', 'a+', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                f.seek(0)
                if f.read(1) == "":
                    writer.writerow(['Nama', 'Hari', 'Tanggal', 'Waktu/Status'])
                writer.writerow([name, day_name_str, today_str, time_or_status])
            log_display = f"{name} | {time_or_status}"
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{log_display}\n")
            self.log_textbox.configure(state="disabled")

    def mark_attendance(self, name):
        time_str = datetime.now().strftime('%H:%M:%S')
        self.log_entry(name, time_str)

    def start_attendance(self):
        self.attendance_mode = True
        self.start_button.configure(state="disabled", fg_color="gray")
        self.stop_button.configure(state="normal", fg_color="red")
        self.save_button.configure(state="disabled")
        self.set_status_button.configure(state="disabled")

    def stop_attendance(self):
        self.attendance_mode = False
        self.start_button.configure(state="normal", fg_color="green")
        self.stop_button.configure(state="disabled", fg_color="gray")
        self.save_button.configure(state="normal")
        self.set_status_button.configure(state="normal")
            
    def on_closing(self):
        self.cap.release()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    app = App()
    app.mainloop()