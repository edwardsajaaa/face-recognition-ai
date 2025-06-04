import cv2
import os

# Folder untuk menyimpan dataset wajah
path = 'gambar_kehadiran'

# Buat folder jika belum ada
if not os.path.exists(path):
    os.makedirs(path)
    print(f"Folder '{path}' berhasil dibuat.")

# Inisialisasi kamera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Tidak dapat membuka kamera.")
    exit()

# Minta input nama dari pengguna
nama = input("Masukkan nama Anda untuk pendaftaran (tanpa spasi, misal: budi_santoso): ")
print("\nSiapkan wajah Anda di depan kamera.")
print("Tekan tombol 's' untuk menyimpan gambar, atau 'q' untuk keluar.")

while True:
    # Ambil frame dari kamera
    ret, frame = cap.read()
    if not ret:
        print("Gagal mengambil frame.")
        break

    # Tampilkan instruksi pada layar
    cv2.putText(frame, "Tekan 's' untuk simpan, 'q' untuk keluar", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Tampilkan video feed
    cv2.imshow('Pendaftaran Wajah - Tekan s untuk Simpan', frame)

    # Tunggu input keyboard
    key = cv2.waitKey(1) & 0xFF

    # Jika tombol 's' ditekan, simpan gambar
    if key == ord('s'):
        # Buat nama file
        nama_file = f"{path}/{nama}.jpg"
        # Simpan frame saat ini sebagai gambar
        cv2.imwrite(nama_file, frame)
        print(f"Gambar berhasil disimpan sebagai {nama_file}")
        break # Keluar dari loop setelah menyimpan

    # Jika tombol 'q' ditekan, keluar
    elif key == ord('q'):
        print("Pendaftaran dibatalkan.")
        break

# Lepaskan kamera dan tutup semua jendela
cap.release()
cv2.destroyAllWindows()