import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import face_recognition
import os
from datetime import datetime

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Konfigurasi Window Utama ---
        self.title("Sistem Absensi Wajah Cerdas")
        self.geometry("1000x600")
        self.resizable(False, False)

        # Inisialisasi variabel penting
        self.known_face_encodings = []
        self.known_face_names = []
        self.attendance_log = set() # Menggunakan set untuk efisiensi
        self.attendance_mode = False
        self.folder_path = 'gambar_kehadiran'

        # Buat folder jika belum ada
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        # Muat wajah yang sudah terdaftar
        self.load_known_faces()

        # Inisialisasi kamera
        self.cap = cv2.VideoCapture(0)

        # --- Membuat Widget / Komponen UI ---
        self.create_widgets()

        # Mulai loop untuk update frame kamera
        self.update_frame()
        
        # Fungsi saat menutup jendela
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # --- Frame Kiri (Untuk Video) ---
        self.video_frame = ctk.CTkFrame(self, width=640, height=480)
        self.video_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(fill="both", expand=True)

        # --- Frame Kanan (Untuk Kontrol) ---
        self.control_frame = ctk.CTkFrame(self, width=300, height=480)
        self.control_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # --- Pendaftaran ---
        reg_frame = ctk.CTkFrame(self.control_frame)
        reg_frame.pack(pady=20, padx=10, fill="x")
        
        ctk.CTkLabel(reg_frame, text="Pendaftaran Wajah Baru", font=("Arial", 16, "bold")).pack(pady=10)
        self.name_entry = ctk.CTkEntry(reg_frame, placeholder_text="Masukkan nama (contoh: budi_s)")
        self.name_entry.pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(reg_frame, text="Simpan Wajah", command=self.save_face).pack(pady=10, fill="x", padx=10)

        # --- Absensi ---
        att_frame = ctk.CTkFrame(self.control_frame)
        att_frame.pack(pady=20, padx=10, fill="x")

        ctk.CTkLabel(att_frame, text="Kontrol Absensi", font=("Arial", 16, "bold")).pack(pady=10)
        self.start_button = ctk.CTkButton(att_frame, text="Mulai Absensi", command=self.start_attendance, fg_color="green")
        self.start_button.pack(pady=10, fill="x", padx=10)
        self.stop_button = ctk.CTkButton(att_frame, text="Hentikan Absensi", command=self.stop_attendance, fg_color="red", state="disabled")
        self.stop_button.pack(pady=10, fill="x", padx=10)

        # --- Log Kehadiran ---
        log_frame = ctk.CTkFrame(self.control_frame)
        log_frame.pack(pady=20, padx=10, fill="both", expand=True)
        ctk.CTkLabel(log_frame, text="Log Kehadiran Hari Ini", font=("Arial", 14, "bold")).pack(pady=5)
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", font=("Arial", 12))
        self.log_textbox.pack(pady=5, padx=5, fill="both", expand=True)

    def load_known_faces(self):
        self.known_face_encodings = []
        self.known_face_names = []
        print("Memuat data wajah yang tersimpan...")
        for filename in os.listdir(self.folder_path):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                try:
                    image_path = os.path.join(self.folder_path, filename)
                    face_image = face_recognition.load_image_file(image_path)
                    face_encoding = face_recognition.face_encodings(face_image)[0]
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(os.path.splitext(filename)[0])
                except IndexError:
                    print(f"Peringatan: Tidak ada wajah terdeteksi di {filename}, file dilewati.")
        print(f"Selesai. {len(self.known_face_names)} wajah berhasil dimuat.")

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Balik frame secara horizontal untuk efek cermin
            frame = cv2.flip(frame, 1)
            
            # Jika mode absensi aktif, lakukan pengenalan
            if self.attendance_mode:
                # Proses pengenalan wajah (dibuat lebih efisien)
                rgb_small_frame = cv2.cvtColor(cv2.resize(frame, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                for face_encoding, face_loc in zip(face_encodings, face_locations):
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                    name = "Tidak Dikenal"
                    
                    if True in matches:
                        first_match_index = matches.index(True)
                        name = self.known_face_names[first_match_index]
                        self.mark_attendance(name)

                    # Gambar kotak di sekitar wajah
                    top, right, bottom, left = [coord * 4 for coord in face_loc]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name.upper(), (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

            # Konversi gambar OpenCV ke format yang bisa ditampilkan di CustomTkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.video_label.configure(image=img_tk)
            self.video_label.image = img_tk

        # Jadwalkan fungsi ini untuk dijalankan lagi setelah 15ms
        self.after(15, self.update_frame)

    def save_face(self):
        name = self.name_entry.get()
        if not name:
            print("Error: Nama tidak boleh kosong!")
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # Balik frame agar sesuai dengan tampilan
            filename = os.path.join(self.folder_path, f"{name}.jpg")
            cv2.imwrite(filename, frame)
            print(f"Wajah untuk '{name}' berhasil disimpan!")
            self.load_known_faces() # Muat ulang data wajah
            self.name_entry.delete(0, 'end') # Kosongkan input

    def start_attendance(self):
        self.attendance_mode = True
        self.start_button.configure(state="disabled", fg_color="gray")
        self.stop_button.configure(state="normal", fg_color="red")
        print("Mode absensi dimulai.")

    def stop_attendance(self):
        self.attendance_mode = False
        self.start_button.configure(state="normal", fg_color="green")
        self.stop_button.configure(state="disabled", fg_color="gray")
        print("Mode absensi dihentikan.")

    def mark_attendance(self, name):
        today_str = datetime.now().strftime('%Y-%m-%d')
        log_entry = f"{name}-{today_str}"
        
        # Hanya catat jika belum ada di log hari ini
        if log_entry not in self.attendance_log:
            self.attendance_log.add(log_entry)
            now = datetime.now()
            time_str = now.strftime('%H:%M:%S')
            
            # Tulis ke file CSV
            with open('kehadiran.csv', 'a+') as f:
                f.write(f'{name},{today_str},{time_str}\n')
            
            # Update tampilan di log textbox
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{name} | {time_str}\n")
            self.log_textbox.configure(state="disabled")
            print(f"Kehadiran untuk {name} berhasil dicatat.")
            
    def on_closing(self):
        self.cap.release()
        self.destroy()

if __name__ == "__main__":
    # Atur tema tampilan
    ctk.set_appearance_mode("System") # Bisa diganti "Dark" atau "Light"
    ctk.set_default_color_theme("blue") # Bisa diganti "green" atau "dark-blue"
    
    app = App()
    app.mainloop()