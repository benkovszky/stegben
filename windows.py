import sys
import os
import base64
import math
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import ctypes


# ------------------------------------------------------------
# A MEGLÉVŐ STEGANOGRÁFIAI FÜGGVÉNYEK (változatlanok)
# ------------------------------------------------------------

def zero_last_bit(r, g, b):
    r -= r % 2
    g -= g % 2
    b -= b % 2
    return r, g, b

def resource_path(path):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("StegBen")
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, path)

def create_validation_list(image, hidden_length, interval):
    pixels = image.load()
    width, height = image.size
    r, g, b = pixels[5, 56][:3]
    r, g, b = zero_last_bit(r, g, b)
    x_position = abs(width % (width - b))
    y_position = abs(height % (height - r))
    validation_data = [0] * hidden_length
    sample_length = (interval // 200) + 1
    for i in range(hidden_length // interval):
        shift = 0
        interval_mass = 0
        for j in range(sample_length):
            r_sample, g_sample, b_sample = pixels[x_position, y_position][:3]
            r_sample, g_sample, b_sample = zero_last_bit(r_sample, g_sample, b_sample)
            if (r_sample + g_sample + b_sample) % 4 == 2:
                x_position += (width - (r_sample + g_sample + j))
                x_position = abs(x_position % width)
                y_position += (height - (r_sample + b_sample + j))
                y_position = abs(y_position % height)
            else:
                x_position -= (width - (g_sample + b_sample + j))
                x_position = abs(x_position % width)
                y_position -= (height - (r_sample + b_sample + j))
                y_position = abs(y_position % height)
            interval_mass += (r_sample + b_sample + g_sample)
        shift = interval_mass % interval
        for k in range(interval):
            position = i * interval + k
            if position < hidden_length:
                validation_data[position] = 1 if k == shift else 0
    return validation_data

def search_64_bit_key(image):
    pixels = image.load()
    width, height = image.size
    key64 = generate_64_bit_key_from_image(image)
    key_str = ''.join(str(bit) for bit in key64)
    all_extracted_bits = []
    for i in range(width):
        for j in range(height):
            all_extracted_bits.append(str(pixels[i, j][0] & 1))
    binary_data = ''.join(all_extracted_bits)
    key_position = -1
    for start_pos in range(len(binary_data) - 64, -1, -1):
        if binary_data[start_pos:start_pos+64] == key_str:
            key_position = start_pos
            break
    if key_position == -1:
        return ""
    hidden_length = key_position
    return hidden_length

def extraxt_interval(image):
    pixels = image.load()
    width, height = image.size
    interval_bits = ""
    for i in range(32):
        pixel = pixels[width - 1, height - 1 - i]
        interval_bits += str(pixel[0] & 1)
    interval = int(interval_bits, 2)
    return interval

def generate_64_bit_key_from_image(img):
    width, height = img.size
    key64bit = [0] * 64
    pixels = img.load()
    for x in range(64):
        if x < width:
            r, g, b = pixels[0, x][:3]
            r, g, b = zero_last_bit(r, g, b)
            if x % 3 == 0:
                key64bit[x] = 1 if r % 4 == 2 else 0
            elif x % 3 == 1:
                key64bit[x] = 1 if g % 4 == 2 else 0
            else:
                key64bit[x] = 1 if b % 4 == 2 else 0
        else:
            print("Kép túl kicsi")
    return key64bit

def generate_256_bit_key_from_image(img):
    width, height = img.size
    pixels = img.load()
    r, g, b = pixels[0, 0][:3]
    r, g, b = zero_last_bit(r, g, b)
    x_position = r % width
    y_position = g % height
    key_bits = [0] * 256
    for x in range(256):
        r, g, b = pixels[x_position, y_position][:3]
        r, g, b = zero_last_bit(r, g, b)
        if x % 3 == 2:
            key_bits[x] = 1 if r % 4 == 2 else 0
        elif x % 3 == 1:
            key_bits[x] = 1 if g % 4 == 2 else 0
        else:
            key_bits[x] = 1 if b % 4 == 2 else 0
        if x_position % 3 == 2:
            x_position += r + x
        elif x_position % 3 == 1:
            x_position += g + x
        else:
            x_position += b + x
        if y_position % 3 == 2:
            y_position += b + x
        elif y_position % 3 == 1:
            y_position += g + x
        else:
            y_position += r + x
        x_position %= width
        y_position %= height
    bit_str = ''.join(str(b) for b in key_bits)
    byte_val = int(bit_str, 2).to_bytes(32, byteorder='big')
    return byte_val.hex()

def aes_encrypt(text, key_hex):
    try:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError("A kulcs nem 256 bites!")
        iv = key[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_text = pad(text.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_text)
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        raise Exception(f"AES titkosítási hiba: {e}")

def aes_decrypt(encrypted_text, key_hex):
    try:
        key = bytes.fromhex(key_hex)
        if len(key) != 32:
            raise ValueError("A kulcs nem 256 bites!")
        iv = key[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_bytes = base64.b64decode(encrypted_text)
        decrypted = cipher.decrypt(encrypted_bytes)
        unpadded = unpad(decrypted, AES.block_size)
        return unpadded.decode('utf-8')
    except Exception as e:
        raise Exception(f"AES visszafejtési hiba: {e}")

def aes_encrypt_bytes(data: bytes, key_hex: str) -> bytes:
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise ValueError("A kulcs nem 256 bites!")
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def aes_decrypt_bytes(data: bytes, key_hex: str) -> bytes:
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise ValueError("A kulcs nem 256 bites!")
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data), AES.block_size)

def text_to_bits(text):
    data = text.encode("utf-8")
    return ''.join(format(byte, '08b') for byte in data)

def bits_to_text(binary_data):
    byte_array = bytearray(
        int(binary_data[i:i+8], 2)
        for i in range(0, len(binary_data), 8)
        if i + 8 <= len(binary_data)
    )
    return byte_array.decode("utf-8", errors="replace")

def bytes_to_bits(data: bytes) -> str:
    return ''.join(format(byte, '08b') for byte in data)

def bits_to_bytes(bits: str) -> bytes:
    return bytes(
        int(bits[i:i+8], 2)
        for i in range(0, len(bits) - 7, 8)
    )

def embed_text_in_image(image_path, output_path, binary_text):
    img = Image.open(image_path).convert('RGB')
    pixels = img.load()
    width, height = img.size
    interval = int(((width * height) - 200) // len(binary_text))
    interval_bits = format(interval & 0xFFFFFFFF, '032b')
    for i in range(32):
        x, y = width - 1, height - 1 - i
        pixel = list(pixels[x, y])
        pixel[0] = (pixel[0] & ~1) | int(interval_bits[i])
        pixels[x, y] = tuple(pixel)
    hidden_length = len(binary_text) * interval
    validation_list = create_validation_list(img, hidden_length, interval)
    x_position = 6
    y_position = 7
    for i in range(width):
        for j in range(height):
            idx = i * height + j
            if idx >= hidden_length:
                break
            pixel = list(pixels[i, j])
            r_ref, g_ref, b_ref = pixels[x_position, y_position][:3]
            r_ref, g_ref, b_ref = zero_last_bit(r_ref, g_ref, b_ref)
            if validation_list[idx] == 1:
                if (r_ref + g_ref + b_ref) % 6 == 0:
                    pixel[0] = (pixel[0] & ~1) | int(binary_text[idx // interval])
                elif (r_ref + g_ref + b_ref) % 6 == 2:
                    pixel[1] = (pixel[1] & ~1) | int(binary_text[idx // interval])
                elif (r_ref + g_ref + b_ref) % 6 == 4:
                    pixel[2] = (pixel[2] & ~1) | int(binary_text[idx // interval])
            pixels[i, j] = tuple(pixel)
            if (r_ref + g_ref + b_ref) % 4 == 2:
                x_position += (width - (r_ref + g_ref + j))
                x_position = abs(x_position % width)
                y_position += (height - (r_ref + b_ref + j))
                y_position = abs(y_position % height)
            else:
                x_position -= (width - (g_ref + b_ref + j))
                x_position = abs(x_position % width)
                y_position -= (height - (r_ref + b_ref + j))
                y_position = abs(y_position % height)
    key64bit = generate_64_bit_key_from_image(img)
    for k in range(64):
        idx = hidden_length + k
        i = idx // height
        j = idx % height
        if i >= width:
            break
        pixel = list(pixels[i, j])
        pixel[0] = (pixel[0] & ~1) | key64bit[k]
        pixels[i, j] = tuple(pixel)
    img.save(output_path)

def extract_hidden_text_with_key(image):
    pixels = image.load()
    width, height = image.size
    interval = extraxt_interval(image)
    hidden_length = search_64_bit_key(image)
    if hidden_length == "":
        return ""
    validation_data = create_validation_list(image, hidden_length, interval)
    extracted_binary = [0] * (hidden_length // interval)
    x_position = 6
    y_position = 7
    for i in range(width):
        for j in range(height):
            idx = i * height + j
            if idx >= hidden_length:
                break
            pixel = list(pixels[i, j])
            r_ref, g_ref, b_ref = pixels[x_position, y_position][:3]
            r_ref, g_ref, b_ref = zero_last_bit(r_ref, g_ref, b_ref)
            if validation_data[idx] == 1:
                bit_index = idx // interval
                if (r_ref + g_ref + b_ref) % 6 == 0:
                    extracted_binary[bit_index] = pixel[0] & 1
                elif (r_ref + g_ref + b_ref) % 6 == 2:
                    extracted_binary[bit_index] = pixel[1] & 1
                elif (r_ref + g_ref + b_ref) % 6 == 4:
                    extracted_binary[bit_index] = pixel[2] & 1
            pixels[i, j] = tuple(pixel)
            if (r_ref + g_ref + b_ref) % 4 == 2:
                x_position += (width - (r_ref + g_ref + j))
                x_position = abs(x_position % width)
                y_position += (height - (r_ref + b_ref + j))
                y_position = abs(y_position % height)
            else:
                x_position -= (width - (g_ref + b_ref + j))
                x_position = abs(x_position % width)
                y_position -= (height - (r_ref + b_ref + j))
                y_position = abs(y_position % height)
    binary_string = ''.join(str(bit) for bit in extracted_binary)
    return bits_to_text(binary_string)

def hidden_image_to_bits(base_image_path, hidden_image_path, key_hex: str):
    img = Image.open(base_image_path)
    hidden_img = Image.open(hidden_image_path)
    width_base, height_base = img.size
    width_hidden, height_hidden = hidden_img.size
    hidden_image_size = width_hidden * height_hidden
    base_image_size = height_base * width_base
    resized_image_max_size = (base_image_size // 8) - 64 - 16
    if hidden_image_size > resized_image_max_size:
        resize_value = resized_image_max_size / hidden_image_size
        width_hidden = math.floor(width_hidden * resize_value)
        height_hidden = math.floor(height_hidden * resize_value)
        hidden_img = hidden_img.resize((width_hidden, height_hidden))
    raw_bytes = bytearray()
    for pixel in hidden_img.getdata():
        for channel in pixel[:3]:
            raw_bytes.append(channel)
    encrypted_bytes = aes_encrypt_bytes(bytes(raw_bytes), key_hex)
    encrypted_bits = bytes_to_bits(encrypted_bytes)
    width_bits = format(width_hidden & 0xFFFF, '016b')
    height_bits = format(height_hidden & 0xFFFF, '016b')
    resolution_bits = width_bits + height_bits
    enc_len = len(encrypted_bits)
    length_bits = format(enc_len & 0xFFFFFFFF, '032b')
    return encrypted_bits, resolution_bits, length_bits

def hidden_bits_to_image(image_path, output_path, encrypted_bits, resolution_bits, length_bits):
    img = Image.open(image_path)
    pixels = img.load()
    width, height = img.size
    for i in range(width):
        for j in range(height):
            pixel = list(pixels[i, j])
            for k in range(3):
                idx = (3 * (i * height + j)) + k
                if idx < len(encrypted_bits):
                    pixel[k] = (pixel[k] & ~1) | int(encrypted_bits[idx])
            pixels[i, j] = tuple(pixel)
    metadata_bits = resolution_bits + length_bits
    for i in range(64):
        pixel = list(pixels[width - 1 - i, height - 1])
        pixel[0] = (pixel[0] & ~1) | int(metadata_bits[i])
        pixels[width - 1 - i, height - 1] = tuple(pixel)
    img.save(output_path)

def extract_hidden_image(image_path, output_path, key_hex: str):
    base_image = Image.open(image_path)
    pixels = base_image.load()
    width_base, height_base = base_image.size
    metadata_bits = ""
    for i in range(64):
        pixel = pixels[width_base - 1 - i, height_base - 1]
        metadata_bits += str(pixel[0] & 1)
    resolution_bits = metadata_bits[:32]
    length_bits = metadata_bits[32:64]
    width_hidden = int(resolution_bits[:16], 2)
    height_hidden = int(resolution_bits[16:], 2)
    enc_data_len = int(length_bits, 2)
    encrypted_bits = ""
    for i in range(width_base):
        for j in range(height_base):
            if len(encrypted_bits) >= enc_data_len:
                break
            pixel = pixels[i, j]
            for k in range(3):
                if len(encrypted_bits) < enc_data_len:
                    encrypted_bits += str(pixel[k] & 1)
        if len(encrypted_bits) >= enc_data_len:
            break
    encrypted_bytes = bits_to_bytes(encrypted_bits[:enc_data_len])
    raw_bytes = aes_decrypt_bytes(encrypted_bytes, key_hex)
    hidden_pixels = []
    for i in range(0, len(raw_bytes) - 2, 3):
        r = raw_bytes[i]
        g = raw_bytes[i + 1]
        b = raw_bytes[i + 2]
        hidden_pixels.append((r, g, b))
    hidden_img = Image.new("RGB", (width_hidden, height_hidden))
    hidden_img.putdata(hidden_pixels)
    hidden_img.save(output_path)
    return output_path

# ------------------------------------------------------------
# CUSTOMTKINTER UI
# ------------------------------------------------------------

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.iconbitmap(resource_path("icon.ico"))
        self.after(100, lambda: self.iconbitmap(resource_path("icon.ico")))
        self.title("StegBen")
        self.geometry("950x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Változók a szöveg tabhoz
        self.text_image_path = None
        self.text_image = None
        self.text_key_image_path = None
        self.text_key_image = None
        self.text_key_hex = None

        # Változók a kép tabhoz
        self.image_base_path = None
        self.image_base = None
        self.image_hidden_path = None
        self.image_hidden = None
        self.image_key_image_path = None
        self.image_key_image = None
        self.image_key_hex = None

        # Fő tabok
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)

        self.tabview.add("Szöveg")
        self.tabview.add("Kép")

        self.setup_text_tab()
        self.setup_image_tab()

        # Státusz sor
        self.status_label = ctk.CTkLabel(self, text="Készen áll", anchor="w")
        self.status_label.pack(pady=5, padx=10, fill="x")

    # ------------------------------------------------------------
    # SEGÉDFÜGGVÉNYEK
    # ------------------------------------------------------------
    def set_status(self, msg):
        self.status_label.configure(text=msg)

    def generate_key_from_image(self, img) -> str:
        if img is None:
            return None
        return generate_256_bit_key_from_image(img)

    # ------------------------------------------------------------
    # SZÖVEG TAB
    # ------------------------------------------------------------
    def setup_text_tab(self):
        tab = self.tabview.tab("Szöveg")

        # Keret: kép kiválasztása
        frame1 = ctk.CTkFrame(tab)
        frame1.pack(pady=5, padx=10, fill="x")

        self.text_image_label = ctk.CTkLabel(frame1, text="Nincs kép kiválasztva")
        self.text_image_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        btn_select = ctk.CTkButton(frame1, text="Kép kiválasztása", command=self.select_text_image)
        btn_select.grid(row=0, column=1, padx=5, pady=5)

        # Checkbox külön kulcsképhez
        self.text_separate_key_var = ctk.IntVar(value=0)
        chk = ctk.CTkCheckBox(frame1, text="Külön kép használata a kulcshoz",
                              variable=self.text_separate_key_var,
                              command=self.toggle_text_key_image)
        chk.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Kulcskép kiválasztás (rejtve, amíg nincs bejelölve)
        self.text_key_frame = ctk.CTkFrame(frame1)
        self.text_key_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.text_key_frame.grid_remove()

        self.text_key_image_label = ctk.CTkLabel(self.text_key_frame, text="Nincs kulcskép kiválasztva")
        self.text_key_image_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        btn_key = ctk.CTkButton(self.text_key_frame, text="Kulcskép betöltése", command=self.select_text_key_image)
        btn_key.grid(row=0, column=1, padx=5, pady=5)

        # Szöveg bevitel placeholder-rel
        txt_frame = ctk.CTkFrame(tab)
        txt_frame.pack(pady=5, padx=10, fill="both", expand=True)

        self.text_edit = ctk.CTkTextbox(txt_frame, height=200)
        self.text_edit.pack(fill="both", expand=True, padx=5, pady=5)

        # Placeholder beállítása
        self.placeholder_text = "Ide írja a rejtendő szöveget..."
        self.text_edit.insert("0.0", self.placeholder_text)
        self.text_edit.bind("<FocusIn>", self.on_text_focus_in)
        self.text_edit.bind("<FocusOut>", self.on_text_focus_out)

        # Művelet gombok
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(pady=5, padx=10, fill="x")

        btn_hide_new = ctk.CTkButton(btn_frame, text="Elrejtés (új kép)", command=self.hide_text_new)
        btn_hide_new.grid(row=0, column=0, padx=5, pady=5)

        btn_modify = ctk.CTkButton(btn_frame, text="Módosítás (eredeti felülírása)", command=self.modify_text_image)
        btn_modify.grid(row=0, column=1, padx=5, pady=5)

        btn_extract = ctk.CTkButton(btn_frame, text="Kinyerés", command=self.extract_text)
        btn_extract.grid(row=0, column=2, padx=5, pady=5)

        btn_copy = ctk.CTkButton(btn_frame, text="Szöveg másolása", command=self.copy_text)
        btn_copy.grid(row=0, column=3, padx=5, pady=5)

    def on_text_focus_in(self, event):
        if self.text_edit.get("0.0", "end").strip() == self.placeholder_text:
            self.text_edit.delete("0.0", "end")

    def on_text_focus_out(self, event):
        if not self.text_edit.get("0.0", "end").strip():
            self.text_edit.insert("0.0", self.placeholder_text)

    def toggle_text_key_image(self):
        if self.text_separate_key_var.get():
            self.text_key_frame.grid()
        else:
            self.text_key_frame.grid_remove()
            self.text_key_image = None
            self.text_key_image_path = None
            self.text_key_image_label.configure(text="Nincs kulcskép kiválasztva")
        self.update_text_key()

    def update_text_key(self):
        if self.text_separate_key_var.get() and self.text_key_image:
            img = self.text_key_image
        elif self.text_image:
            img = self.text_image
        else:
            self.text_key_hex = None
            return
        try:
            self.text_key_hex = self.generate_key_from_image(img)
            self.set_status(f"Szöveg kulcs generálva: {self.text_key_hex[:16]}...")
        except Exception as e:
            self.set_status(f"Hiba a kulcs generálásakor: {e}")
            self.text_key_hex = None

    def select_text_image(self):
        path = filedialog.askopenfilename(filetypes=[("Képfájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if path:
            try:
                self.text_image_path = path
                self.text_image = Image.open(path)
                self.text_image_label.configure(text=os.path.basename(path))
                self.update_text_key()
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült betölteni a képet: {e}")

    def select_text_key_image(self):
        path = filedialog.askopenfilename(filetypes=[("Képfájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if path:
            try:
                self.text_key_image_path = path
                self.text_key_image = Image.open(path)
                self.text_key_image_label.configure(text=os.path.basename(path))
                self.update_text_key()
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült betölteni a kulcsképet: {e}")

    def hide_text_new(self):
        if not self.text_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return
        if not self.text_key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsot generálni!")
            return
        text = self.text_edit.get("0.0", "end").strip()
        if not text or text == self.placeholder_text:
            messagebox.showwarning("Figyelmeztetés", "Írjon be szöveget!")
            return
        try:
            encrypted = aes_encrypt(text, self.text_key_hex)
            bits = text_to_bits(encrypted)
            base, ext = os.path.splitext(self.text_image_path)
            out_path = f"{base}_hidden.png"
            embed_text_in_image(self.text_image_path, out_path, bits)
            self.set_status(f"Szöveg elrejtve: {os.path.basename(out_path)}")
            messagebox.showinfo("Siker", f"Szöveg elrejtve!\nMentve: {out_path}")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba: {e}")

    def modify_text_image(self):
        if not self.text_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return
        if not self.text_key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsot generálni!")
            return
        text = self.text_edit.get("0.0", "end").strip()
        if not text or text == self.placeholder_text:
            messagebox.showwarning("Figyelmeztetés", "Írjon be szöveget!")
            return
        if not messagebox.askyesno("Megerősítés", "Biztosan felülírja az eredeti képet?"):
            return
        try:
            encrypted = aes_encrypt(text, self.text_key_hex)
            bits = text_to_bits(encrypted)
            orig_path = self.text_image_path
            base, ext = os.path.splitext(orig_path)
            if ext.lower() != '.png':
                new_path = base + '.png'
            else:
                new_path = orig_path
            embed_text_in_image(orig_path, new_path, bits)
            if new_path != orig_path:
                os.remove(orig_path)
                self.text_image_path = new_path
                self.text_image = Image.open(new_path)
            else:
                self.text_image = Image.open(orig_path)
            self.text_image_label.configure(text=os.path.basename(self.text_image_path))
            self.set_status(f"Kép módosítva: {os.path.basename(self.text_image_path)}")
            messagebox.showinfo("Siker", "A kép sikeresen módosítva!")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba: {e}")

    def extract_text(self):
        if not self.text_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return
        if not self.text_key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsot generálni!")
            return
        try:
            encrypted_b64 = extract_hidden_text_with_key(self.text_image)
            if not encrypted_b64:
                messagebox.showwarning("Figyelmeztetés", "Nem található rejtett szöveg!")
                return
            plaintext = aes_decrypt(encrypted_b64, self.text_key_hex)
            self.text_edit.delete("0.0", "end")
            self.text_edit.insert("0.0", plaintext)
            self.set_status("Szöveg sikeresen kinyerve és visszafejtve.")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba: {e}")

    def copy_text(self):
        content = self.text_edit.get("0.0", "end").strip()
        if content and content != self.placeholder_text:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.set_status("Szöveg másolva a vágólapra.")

    # ------------------------------------------------------------
    # KÉP TAB
    # ------------------------------------------------------------
    def setup_image_tab(self):
        tab = self.tabview.tab("Kép")

        # Alapkép
        frame_base = ctk.CTkFrame(tab)
        frame_base.pack(pady=5, padx=10, fill="x")

        self.image_base_label = ctk.CTkLabel(frame_base, text="Nincs alapkép kiválasztva")
        self.image_base_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        btn_base = ctk.CTkButton(frame_base, text="Alapkép betöltése", command=self.select_image_base)
        btn_base.grid(row=0, column=1, padx=5, pady=5)

        # Rejtendő kép
        frame_hidden = ctk.CTkFrame(tab)
        frame_hidden.pack(pady=5, padx=10, fill="x")

        self.image_hidden_label = ctk.CTkLabel(frame_hidden, text="Nincs rejtendő kép kiválasztva")
        self.image_hidden_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        btn_hidden = ctk.CTkButton(frame_hidden, text="Rejtendő kép betöltése", command=self.select_image_hidden)
        btn_hidden.grid(row=0, column=1, padx=5, pady=5)

        # Külön kulcskép checkbox – az alapkép keretbe tesszük
        self.image_separate_key_var = ctk.IntVar(value=0)
        chk = ctk.CTkCheckBox(frame_base, text="Külön kép használata a kulcshoz",
                              variable=self.image_separate_key_var,
                              command=self.toggle_image_key_image)
        chk.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Kulcskép kiválasztás (rejtve)
        self.image_key_frame = ctk.CTkFrame(frame_base)
        self.image_key_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.image_key_frame.grid_remove()

        self.image_key_label = ctk.CTkLabel(self.image_key_frame, text="Nincs kulcskép kiválasztva")
        self.image_key_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        btn_key = ctk.CTkButton(self.image_key_frame, text="Kulcskép betöltése", command=self.select_image_key_image)
        btn_key.grid(row=0, column=1, padx=5, pady=5)

        # Művelet gombok
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(pady=5, padx=10, fill="x")

        btn_hide = ctk.CTkButton(btn_frame, text="Kép elrejtése", command=self.hide_image)
        btn_hide.grid(row=0, column=0, padx=5, pady=5)

        btn_extract = ctk.CTkButton(btn_frame, text="Kép kinyerése", command=self.extract_image)
        btn_extract.grid(row=0, column=1, padx=5, pady=5)

    def toggle_image_key_image(self):
        if self.image_separate_key_var.get():
            self.image_key_frame.grid()
        else:
            self.image_key_frame.grid_remove()
            self.image_key_image = None
            self.image_key_image_path = None
            self.image_key_label.configure(text="Nincs kulcskép kiválasztva")
        self.update_image_key()

    def update_image_key(self):
        if self.image_separate_key_var.get() and self.image_key_image:
            img = self.image_key_image
        elif self.image_base:
            img = self.image_base
        else:
            self.image_key_hex = None
            return
        try:
            self.image_key_hex = self.generate_key_from_image(img)
            self.set_status(f"Kép kulcs generálva: {self.image_key_hex[:16]}...")
        except Exception as e:
            self.set_status(f"Hiba a kulcs generálásakor: {e}")
            self.image_key_hex = None

    def select_image_base(self):
        path = filedialog.askopenfilename(filetypes=[("Képfájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if path:
            try:
                self.image_base_path = path
                self.image_base = Image.open(path)
                self.image_base_label.configure(text=os.path.basename(path))
                self.update_image_key()
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült betölteni az alapképet: {e}")

    def select_image_hidden(self):
        path = filedialog.askopenfilename(filetypes=[("Képfájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if path:
            try:
                self.image_hidden_path = path
                self.image_hidden = Image.open(path)
                self.image_hidden_label.configure(text=os.path.basename(path))
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült betölteni a rejtendő képet: {e}")

    def select_image_key_image(self):
        path = filedialog.askopenfilename(filetypes=[("Képfájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if path:
            try:
                self.image_key_image_path = path
                self.image_key_image = Image.open(path)
                self.image_key_label.configure(text=os.path.basename(path))
                self.update_image_key()
            except Exception as e:
                messagebox.showerror("Hiba", f"Nem sikerült betölteni a kulcsképet: {e}")

    def hide_image(self):
        if not self.image_base:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy alapképet!")
            return
        if not self.image_hidden:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy rejtendő képet!")
            return
        if not self.image_key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsot generálni!")
            return
        try:
            encrypted_bits, res_bits, len_bits = hidden_image_to_bits(
                self.image_base_path, self.image_hidden_path, self.image_key_hex
            )
            # Automatikus kimeneti név
            base, ext = os.path.splitext(self.image_base_path)
            out_name = f"{base}_with_hidden.png"
            hidden_bits_to_image(self.image_base_path, out_name, encrypted_bits, res_bits, len_bits)
            self.set_status(f"Kép elrejtve: {os.path.basename(out_name)}")
            messagebox.showinfo("Siker", f"Kép sikeresen elrejtve és titkosítva!\nMentve: {out_name}")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba: {e}")

    def extract_image(self):
        if not self.image_base:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy alapképet (ami tartalmazza a rejtett képet)!")
            return
        if not self.image_key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsot generálni!")
            return
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            extract_hidden_image(self.image_base_path, tmp_path, self.image_key_hex)

            # Előnézeti ablak
            self.preview_window = ctk.CTkToplevel(self)
            self.preview_window.title("Kinyert és visszafejtett kép")
            self.preview_window.geometry("500x500")

            preview_img = Image.open(tmp_path)
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(preview_img.resize((400, 400), Image.Resampling.LANCZOS))
            label = ctk.CTkLabel(self.preview_window, image=photo, text="")
            label.image = photo
            label.pack(pady=10)

            def save_extracted():
                save_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                         filetypes=[("PNG kép", "*.png")])
                if save_path:
                    import shutil
                    shutil.copy(tmp_path, save_path)
                    self.set_status(f"Kép mentve: {os.path.basename(save_path)}")
                    messagebox.showinfo("Siker", f"Kép mentve:\n{save_path}")

            btn_save = ctk.CTkButton(self.preview_window, text="Kép mentése", command=save_extracted)
            btn_save.pack(pady=10)

            self.set_status("Kép sikeresen kinyerve és visszafejtve.")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba: {e}")

# ------------------------------------------------------------
# INDÍTÁS
# ------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()