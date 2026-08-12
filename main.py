import sys
import os
import base64
import math
import shutil
import tempfile
from PIL import Image, ImageTk
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Modern UI könyvtárak
import customtkinter as ctk
from tkinter import filedialog, messagebox
import ctypes

#segédfüggvények
def zero_last_bit(r, g, b):
    r -= r % 2
    g -= g % 2
    b -= b % 2
    return r, g, b

def resource_path(path):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, path)

def reverse(number):
    if number == 1:
        return 0
    else:
        return 1

#validációs lista elkészítése
def create_validation_list(image, hidden_length, interval):
    pixels = image.load()
    width, height = image.size
    #kezdő mintavétel beállítása
    r, g, b = pixels[5, 56][:3]
    r, g, b = zero_last_bit(r,g, b)

    x_position = abs(width % (width - b))
    y_position = abs(height % (height - r))


    #lista előre feltöltése a méret miatt
    validation_data = [0] * hidden_length
    sample_length = (interval//200)+1

    for i in range(hidden_length//interval):
        shift = 0
        interval_mass = 0

        #eltolás mértékének kiszámítása

        for j in range(sample_length):
            r_sample, g_sample, b_sample = pixels[x_position, y_position][:3]
            r_sample, g_sample, b_sample = zero_last_bit(r_sample, g_sample, b_sample)

            #mintavétel eltolása
            if r_sample + g_sample + b_sample % 4 == 2:
                x_position += (width - (r_sample + g_sample + j))
                x_position = abs(x_position % width)
                y_position += (height - (r_sample + b_sample + j))
                y_position = abs(y_position % height)
            else:
                x_position -= (width - (g_sample + b_sample + j))
                x_position = abs(x_position % width)
                y_position -= (height - (r_sample + b_sample + j))
                y_position = abs(y_position % height)
            interval_mass += (r_sample + b_sample+ g_sample)
            #shift túlcsordulás kezelése
        shift = interval_mass % interval

        #tömb feltöltése
        for k in range(interval):
            position = i * interval + k
            if position < hidden_length:
                if k == shift:
                    validation_data[position] = 1
                else:
                    validation_data[position] = 0
    return validation_data

#64 bites kulcs keresése
def search_64_bit_key(image):
    pixels = image.load()
    width, height = image.size
    # 1. 64 bites kulcs előállítása a képből
    key64 = generate_64_bit_key_from_image(image)
    key_str = ''.join(str(bit) for bit in key64)

    # 2. Összes bit kiolvasása a piros csatorna LSB-jéből (ugyanolyan sorrendben)
    all_extracted_bits = []
    for i in range(width):
        for j in range(height):
            all_extracted_bits.append(str(pixels[i, j][0] & 1))
    binary_data = ''.join(all_extracted_bits)

    # 3. Kulcs keresése visszafelé
    key_position = -1
    for start_pos in range(len(binary_data) - 64, -1, -1):
        if binary_data[start_pos:start_pos+64] == key_str:
            key_position = start_pos
            break
    if key_position == -1:
        print("A 64 bites kulcs nem található!")
        return ""

    hidden_length = key_position
    print(f"Rejtett adat hossza (bitekben): {hidden_length}")
    return hidden_length

#64 bites kulcs a szöveg végének megtalálásához
def generate_64_bit_key_from_image(img):
    width, height = img.size
    key64bit=[0]*64
    pixels=img.load()
    for x in range(64):
        if x < width:
            r, g, b = pixels[0, x][:3]
            #az utolsó bitet átírom 0-ra
            r, g, b = zero_last_bit(r, g, b)
            #felváltva olvasom ki az R G B értékeket
            if x%3==0:
                if r%4==2:
                    key64bit[x]=1
                else:
                    key64bit[x]=0
            if x%3==1:
                if g%4==2:
                    key64bit[x]=1
                else:
                    key64bit[x]=0
            if x%3==2:
                if b%4==2:
                    key64bit[x]=1
                else:
                    key64bit[x]=0
        else:
            print("Kép túl kicsi")
    return key64bit

#64 bites kulcs elrejtése
def hide_64_bit_key(hidden_length, pixels, width, height, key64bit):
    for k in range(64):
        idx = hidden_length + k
        i = idx // height
        j = idx % height
        if i >= width:
            break
        pixel = list(pixels[i, j])
        pixel[0] = (pixel[0] & ~1) | key64bit[k]
        pixels[i, j] = tuple(pixel)

#256 bites kulcs az AES titkosításhoz
def generate_256_bit_key_from_image(img):
    width, height = img.size
    pixels = img.load()
    #kezdő pozíció beállítása
    r, g, b = pixels[0, 0][:3]
    r, g, b = zero_last_bit(r, g, b)
    x_position = r
    y_position = g
    if x_position >= width:
        x_position -= width
    if y_position >= height:
        y_position -= height
    key256bit = [0] * 256
    #mintavételezés
    for x in range(256):
        r, g, b = pixels[x_position, y_position][:3]
        r, g, b = zero_last_bit(r, g, b)
        
        if x % 3 == 2:
            if r % 4 == 2:
                key256bit[x] = 1
            else:
                key256bit[x] = 0
        if x % 3 == 1:
            if g % 4 == 2:
                key256bit[x] = 1
            else:
                key256bit[x] = 0
        if x % 3 == 0:
            if b % 4 == 2:
                key256bit[x] = 1
            else:
                key256bit[x] = 0
        
        # Pozíció frissítése
      
        if x_position % 3 == 2:
            x_position += r + x
        if x_position % 3 == 1:
            x_position += g + x
        if x_position % 3 == 0:
            x_position += b + x

        if y_position % 3 == 2:
            y_position += b + x
        if y_position % 3 == 1:
            y_position += g + x
        if y_position % 3 == 0:
            y_position += r + x
        
        # Túlcsordulás kezelése modulus segítségével
        x_position = x_position % width
        y_position = y_position % height

    return key256bit

#szöveg titkosítása AES kulcs segítségével
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

#szöveg visszafejtése AES kulcs segítségével
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

#kép titkosítása AES kulcs segítségével
def aes_encrypt_bytes(data: bytes, key_hex: str) -> bytes:
    """Nyers bytes titkosítása AES-CBC-vel, visszaad bytes-t."""
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise ValueError("A kulcs nem 256 bites!")
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

#kép titkosításának a visszafejtése AES kulcs segítségével
def aes_decrypt_bytes(data: bytes, key_hex: str) -> bytes:
    """Titkosított bytes visszafejtése AES-CBC-vel."""
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise ValueError("A kulcs nem 256 bites!")
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data), AES.block_size)

#szöveg bitekké alakítása
def text_to_bits(text):
    data = text.encode("utf-8")
    return ''.join(format(byte, '08b') for byte in data)

#bitek szöveggé alakítása
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

#interval elrejtése 
def embed_interval(interval, pixels, width, height):
    interval_bits = [int(bit) for bit in format(interval & 0xFFFFFFFF, '032b')]
    interval_bits = interval_encryption(pixels, interval_bits, width, height)
    x_position = 6
    y_position = 7


    for i in range(32):
        x, y = width - 1, height - 1 - i
        pixel = list(pixels[x, y])
        r, g, b = pixels[x_position, y_position][:3]
        r, g, b = zero_last_bit(r, g, b)
        selected_channel = ((r+g+b)//2)%3
        pixel[selected_channel] = (pixel[selected_channel] & ~1) | interval_bits[i]
        pixels[x, y] = tuple(pixel)
        x_position+= r +b
        y_position+= r+g
        x_position = x_position % width
        y_position = y_position % height

#interval kinyerése
def extract_interval(image):
    pixels = image.load()
    width, height = image.size
    # intervallum bitjeinek kinyerése
    interval_bits = []
    x_position = 6
    y_position = 7


    for i in range(32):
        pixel = pixels[width - 1, height - 1 - i]
        r, g, b = pixels[x_position, y_position][:3]
        r, g, b = zero_last_bit(r, g, b)
        selected_channel = ((r+g+b)//2)%3
        interval_bits.append(pixel[selected_channel] & 1)
        x_position+= r +b
        y_position+= r+g
        x_position = x_position % width
        y_position = y_position % height
    decrypted_interval = interval_encryption(pixels, interval_bits, width, height)
    # bitek visszaalakítása
    interval = int(''.join(map(str, decrypted_interval)), 2)
    print(f"Kinyert intervallum: {interval}")
    return interval        

#interval bit szintű titkosítása
def interval_encryption(pixels, interval_bits, width, height):
    encrypted_interval_bits = [0] * 32
    x_position = 6
    y_position = 7
    channel = 0
    for i in range(32):
        r, g, b = pixels[x_position, y_position][:3]
        r, g, b = zero_last_bit(r, g, b)
        if (r + g + b) %6 == 2:
            channel = r
        if (r + g + b) %6 == 4:
            channel = g
        if (r + g + b) %6 == 0:
            channel = b
        reference = (channel>>((i%7)+1)) & 1
        #print(f"A szám: {reference}")
        if reference == 0:
            encrypted_interval_bits[i]= interval_bits[i]
        else:
            encrypted_interval_bits[i] = reverse(interval_bits[i])

        #mintavétel pozíciójának frissítése
        x_position+= r +b
        y_position+= r+g
        x_position = x_position % width
        y_position = y_position % height
    return encrypted_interval_bits

#szöveg elrejtése a képben
def embed_text_in_image(image_path, output_path, binary_text):
    img = Image.open(image_path).convert('RGB')
    pixels = img.load()
    width, height = img.size
    interval = int(((width * height)- 200) // len(binary_text))

    #interval elrejtése
    embed_interval(interval, pixels, width, height)

    hidden_length = len(binary_text) * interval
    print("az interval értéke: ", interval)
    print("Elrejtett adat hossza: ", hidden_length)

    #validációs lista elkészítése
    validation_list = create_validation_list(img, hidden_length, interval)

    #kezdő pozíció inicializálása
    x_position = 6
    y_position = 7
    for i in range(width):
        for j in range(height):
            idx = i * height + j
            if idx >= hidden_length:
                break
            
            #pixel módosítása listává alakítva
            pixel = list(pixels[i, j])
            r_ref, g_ref, b_ref = pixels[x_position, y_position][:3]
            r_ref, g_ref, b_ref = zero_last_bit(r_ref, g_ref, b_ref)


            if validation_list[idx] == 1:
                if (r_ref + g_ref + b_ref) % 6 == 0:
                    pixel[0] = (pixel[0] & ~1) | int(binary_text[idx//interval])
                elif (r_ref + g_ref + b_ref) % 6 == 2:
                    pixel[1] = (pixel[1] & ~1) | int(binary_text[idx//interval])
                elif (r_ref + g_ref + b_ref) % 6 == 4:
                    pixel[2] = (pixel[2] & ~1) | int(binary_text[idx//interval])

            pixels[i, j] = tuple(pixel)
            #mintavétel eltolása, és döntés a shift növeléséről
            if r_ref + g_ref + b_ref % 4 == 2:
        
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
    hide_64_bit_key(hidden_length, pixels, width, height, key64bit)
      
    img.save(output_path)

#szöveg kinyerése
def extract_hidden_text_with_key(image):
    pixels = image.load()
    width, height = image.size
    
    interval = extract_interval(image)
    hidden_length = search_64_bit_key(image)
    validation_data = create_validation_list(image, hidden_length, interval)


    extracted_binary = [0] * (hidden_length // interval)

    x_position = 6
    y_position = 7
    for i in range(width):
        for j in range(height):
            idx = i * height + j
            if idx >= hidden_length:
                break
            
            #pixel módosítása listává alakítva
            pixel = list(pixels[i, j])
            r_ref, g_ref, b_ref = pixels[x_position, y_position][:3]
            r_ref, g_ref, b_ref = zero_last_bit(r_ref, g_ref, b_ref)


            if validation_data[idx]==1:
                bit_index = idx // interval
                if (r_ref + g_ref + b_ref) % 6 == 0:
                    extracted_binary[bit_index] = pixel[0] & 1
                elif (r_ref + g_ref + b_ref) % 6 == 2:
                    extracted_binary[bit_index] = pixel[1] & 1
                elif (r_ref + g_ref + b_ref) % 6 == 4:
                    extracted_binary[bit_index] = pixel[2] & 1

            pixels[i, j] = tuple(pixel)
            #mintavétel eltolása, és döntés a shift növeléséről
            if r_ref + g_ref + b_ref % 4 == 2:
        
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
    hidden_text = bits_to_text(binary_string)



    return hidden_text

def hidden_image_to_bits(base_image_path, hidden_image_path, key_hex: str):
    """
    A rejtendő kép pixeleit AES-sel titkosítja, majd bitekké alakítja.
    Visszaad: (titkosított_bitek, felbontás_bitek, hossz_bitek)
    """
    img = Image.open(base_image_path)
    hidden_img = Image.open(hidden_image_path)
    width_base_image, height_base_image = img.size
    width_hidden_image, height_hidden_image = hidden_img.size

    #méretek számítása - AES padding miatt ~16 bájttal több helyet hagyunk
    hidden_image_size = width_hidden_image * height_hidden_image
    base_image_size = height_base_image * width_base_image
    resized_image_max_size = (base_image_size // 8) - 64 - 16

    #szükség esetén átméretezi a képet
    if hidden_image_size > resized_image_max_size:
        resize_value = resized_image_max_size / hidden_image_size
        width_hidden_image = math.floor(width_hidden_image * resize_value)
        height_hidden_image = math.floor(height_hidden_image * resize_value)
        hidden_img = hidden_img.resize((width_hidden_image, height_hidden_image))

    # Pixel adatok összegyűjtése bytes-ként - csak RGB-t kezelünk
    raw_bytes = bytearray()
    for pixel in hidden_img.getdata():
        for channel in pixel[:3]:
            raw_bytes.append(channel)

    # AES titkosítás
    encrypted_bytes = aes_encrypt_bytes(bytes(raw_bytes), key_hex)
    encrypted_bits = bytes_to_bits(encrypted_bytes)

    # Felbontás bitekben (32 bit - 4 bájt)
    width_bits = format(width_hidden_image & 0xFFFF, '016b')
    height_bits = format(height_hidden_image & 0xFFFF, '016b')
    resolution_bits = width_bits + height_bits

    # A titkosított adat hosszát is eltároljuk (32 bit = max ~4 milliárd bit)
    enc_len = len(encrypted_bits)
    length_bits = format(enc_len & 0xFFFFFFFF, '032b')

    return encrypted_bits, resolution_bits, length_bits

#kép elrejtése a képben
def hidden_bits_to_image(image_path, output_path, encrypted_bits, resolution_bits, length_bits):

    img = Image.open(image_path)
    pixels = img.load()
    width, height = img.size

    #kép bitjeinek elrejtése a 3 csatorna használata segítségével
    for i in range(width):
        for j in range(height):
            pixel = list(pixels[i, j])
            for k in range(3):
                idx = (3 * (i * height + j)) + k
                if idx < len(encrypted_bits):
                    pixel[k] = (pixel[k] & ~1) | int(encrypted_bits[idx])
            pixels[i, j] = tuple(pixel)

    # Metadata elrejtése az utolsó sorban (jobb saroktól balra)
    # 32 bit: felbontás (szélesség + magasság), 32 bit: titkosított adat hossza
    metadata_bits = resolution_bits + length_bits  # 64 bit
    for i in range(64):
        pixel = list(pixels[width - 1 - i, height - 1])
        pixel[0] = (pixel[0] & ~1) | int(metadata_bits[i])
        pixels[width - 1 - i, height - 1] = tuple(pixel)

    img.save(output_path)
    print("A titkosított kép elrejtése sikeres")

#kép kinyerése
def extract_hidden_image(image_path, output_path, key_hex: str):

    base_image = Image.open(image_path)
    pixels = base_image.load()
    width_base_image, height_base_image = base_image.size

    # Metadata olvasása (64 bit az utolsó sorból)
    metadata_bits = ""
    for i in range(64):
        pixel = pixels[width_base_image - 1 - i, height_base_image - 1]
        metadata_bits += str(pixel[0] & 1)

    # felbontás és hossza visszaalakítása
    resolution_bits = metadata_bits[:32]
    length_bits = metadata_bits[32:64]

    width_hidden_image = int(resolution_bits[:16], 2)
    height_hidden_image = int(resolution_bits[16:], 2)
    enc_data_len = int(length_bits, 2)

    print(f"Rejtett kép mérete: {width_hidden_image}x{height_hidden_image}")
    print(f"Titkosított adatok hossza (bit): {enc_data_len}")

    # Titkosított bitek kiolvasása
    encrypted_bits = ""
    for i in range(width_base_image):
        for j in range(height_base_image):
            if len(encrypted_bits) >= enc_data_len:
                break
            pixel = pixels[i, j]
            for k in range(3):
                if len(encrypted_bits) < enc_data_len:
                    encrypted_bits += str(pixel[k] & 1)
        if len(encrypted_bits) >= enc_data_len:
            break

    # Bitek → bytes → AES visszafejtés
    encrypted_bytes = bits_to_bytes(encrypted_bits[:enc_data_len])
    raw_bytes = aes_decrypt_bytes(encrypted_bytes, key_hex)

    # bitek visszaalakítása pixelekké
    hidden_pixels = []
    for i in range(0, len(raw_bytes) - 2, 3):
        r = raw_bytes[i]
        g = raw_bytes[i + 1]
        b = raw_bytes[i + 2]
        hidden_pixels.append((r, g, b))

    hidden_img = Image.new("RGB", (width_hidden_image, height_hidden_image))
    hidden_img.putdata(hidden_pixels)
    hidden_img.save(output_path)
    print(f"Titkosított rejtett kép kinyerve és visszafejtve: {output_path}")

# ============================================================
# MODERN FELHASZNÁLÓI FELÜLET 
# ============================================================

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class SteganographyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("StegBen")
        self.geometry("850x670")
        self.minsize(750, 550)

        # Adatváltozók
        self.current_image_path = None
        self.current_image = None
        self.key_image_path = None
        self.key_image = None
        self.base_image_path = None
        self.base_image = None
        self.hidden_image_path = None
        self.hidden_image = None
        self.key_image_path_img = None
        self.key_image_img = None
        self.current_key64 = None
        self.current_key256_hex = None

        # Fő füles panel (Tabview)
        self.tabview = ctk.CTkTabview(self, width=800, height=570)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tabview.add("Szöveg elrejtése/kinyerése")
        self.tabview.add("Kép elrejtése/kinyerése")

        self.setup_text_tab()
        self.setup_image_tab()

        # Státusz sáv legalul
        self.lbl_status = ctk.CTkLabel(self, text="Kész", anchor="w", font=("Helvetica", 12, "italic"))
        self.lbl_status.pack(side="bottom", fill="x", padx=20, pady=5)

    def set_status(self, text):
        self.lbl_status.configure(text=text)

    # --- 1. FÜL: SZÖVEG ELRENDEZÉS (GOMBOK BALRA IGAZÍTVA) ---
    def setup_text_tab(self):
        tab = self.tabview.tab("Szöveg elrejtése/kinyerése")

        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=5)

        # Kép elérési út és választó gomb (pontosan balra igazítva)
        self.lbl_text_img_path = ctk.CTkLabel(container, text="Nincs kép kiválasztva", wraplength=700, anchor="w")
        self.lbl_text_img_path.pack(pady=(10, 2), fill="x", anchor="w")

        btn_select_img = ctk.CTkButton(container, text="Kép kiválasztása", command=self.select_image)
        btn_select_img.pack(pady=5, anchor="w")

        # Külön kulcs checkbox (balra igazítva)
        self.chk_sep_key_text_var = ctk.BooleanVar(value=False)
        self.chk_sep_key = ctk.CTkCheckBox(container, text="Külön kép használata a kulcsokhoz", 
                                           variable=self.chk_sep_key_text_var, command=self.toggle_key_image_selection)
        self.chk_sep_key.pack(pady=10, anchor="w")

        # Külön kulcskép panel (Közvetlenül a checkbox ALÁ, de még a szövegmező FÖLÉ kerül)
        self.frame_key_img = ctk.CTkFrame(container, fg_color="transparent")
        
        self.lbl_text_key_path = ctk.CTkLabel(self.frame_key_img, text="Nincs kulcskép kiválasztva", wraplength=700, anchor="w")
        self.lbl_text_key_path.pack(pady=2, fill="x", anchor="w")
        
        self.btn_select_key_text = ctk.CTkButton(self.frame_key_img, text="Kulcskép kiválasztása", command=self.select_key_image)
        self.btn_select_key_text.pack(pady=5, anchor="w")

        # Szövegbeviteli mező (szépen elhelyezve)
        lbl_text_prompt = ctk.CTkLabel(container, text="Szöveg:", font=("Helvetica", 12, "bold"), anchor="w")
        lbl_text_prompt.pack(pady=(10, 2), anchor="w")

        self.text_edit = ctk.CTkTextbox(container, height=150, activate_scrollbars=True)
        self.text_edit.pack(fill="both", expand=True, pady=5)

        # Funkciógombok alul
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 5))
        btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(btn_frame, text="Elrejtés (új kép)", command=self.hide_text_new_image).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Módosítás", command=self.modify_image).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Kinyerés", command=self.extract_text).grid(row=0, column=2, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Szöveg másolása", command=self.copy_text).grid(row=0, column=3, padx=5, sticky="ew")

    # --- 2. FÜL: KÉP ELRENDEZÉS (SZÉPEN EGYMÁS ALÁ IGAZÍTVA, KULCSKÉPPEL A HELYÉN) ---
    def setup_image_tab(self):
        tab = self.tabview.tab("Kép elrejtése/kinyerése")

        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=5)

        # Alapkép szekció (balra igazított gombbal)
        self.lbl_base_path = ctk.CTkLabel(container, text="Nincs alapkép kiválasztva", wraplength=700, anchor="w")
        self.lbl_base_path.pack(pady=(10, 2), fill="x", anchor="w")

        btn_select_base = ctk.CTkButton(container, text="Alapkép kiválasztása", command=self.select_base_image)
        btn_select_base.pack(pady=5, anchor="w")

        # Rejtendő kép szekció (balra igazított gombbal)
        self.lbl_hidden_path = ctk.CTkLabel(container, text="Nincs rejtendő kép kiválasztva", wraplength=700, anchor="w")
        self.lbl_hidden_path.pack(pady=(15, 2), fill="x", anchor="w")

        btn_select_hidden = ctk.CTkButton(container, text="Rejtendő kép kiválasztása", command=self.select_hidden_image)
        btn_select_hidden.pack(pady=5, anchor="w")

        # Kulcskép checkbox (A gombok felett struktúrában, a rejtendő kép alatt közvetlenül)
        self.chk_sep_key_img_var = ctk.BooleanVar(value=False)
        self.chk_sep_key_img = ctk.CTkCheckBox(container, text="Külön kép használata a kulcsokhoz", 
                                              variable=self.chk_sep_key_img_var, command=self.toggle_key_image_selection_img)
        self.chk_sep_key_img.pack(pady=15, anchor="w")

        # Kulcskép al-keret (csak szükség esetén pack-elve, a checkbox után)
        self.frame_key_img_img = ctk.CTkFrame(container, fg_color="transparent")

        self.lbl_img_key_path = ctk.CTkLabel(self.frame_key_img_img, text="Nincs kulcskép kiválasztva", wraplength=700, anchor="w")
        self.lbl_img_key_path.pack(pady=2, fill="x", anchor="w")
        
        self.btn_select_key_img = ctk.CTkButton(self.frame_key_img_img, text="Kulcskép kiválasztása", command=self.select_key_image_img)
        self.btn_select_key_img.pack(pady=5, anchor="w")

        # Műveleti gombok legalul
        btn_frame_img = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame_img.pack(side="bottom", fill="x", pady=20)
        btn_frame_img.columnconfigure((0, 1), weight=1)

        btn_hide_img = ctk.CTkButton(btn_frame_img, text="Kép elrejtése", command=self.hide_image, height=42)
        btn_hide_img.grid(row=0, column=0, padx=10, sticky="ew")

        btn_extract_img = ctk.CTkButton(btn_frame_img, text="Kép kinyerése", command=self.extract_image, height=42)
        btn_extract_img.grid(row=0, column=1, padx=10, sticky="ew")

    # --- DINAMIKUS PANEL JELENLÉT VEZÉRLÉS ---

    def toggle_key_image_selection(self):
        if self.chk_sep_key_text_var.get():
            # Pontosan a checkbox alá pack-eli be a kulcsképválasztót
            self.frame_key_img.pack(pady=5, fill="x", after=self.chk_sep_key)
        else:
            self.frame_key_img.pack_forget()
            self.key_image_path = None
            self.key_image = None
            self.update_keys_from_images()

    def toggle_key_image_selection_img(self):
        if self.chk_sep_key_img_var.get():
            # Pontosan a checkbox alá pack-eli be a képek fülön a kulcsképválasztót
            self.frame_key_img_img.pack(pady=5, fill="x", after=self.chk_sep_key_img)
        else:
            self.frame_key_img_img.pack_forget()
            self.key_image_path_img = None
            self.key_image_img = None

    # --- ESZKÖZTÁR ÉS INTERAKCIÓK ---

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Kép kiválasztása a szöveghez",
            filetypes=[("Kép fájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if file_path:
            try:
                self.current_image_path = file_path
                self.current_image = Image.open(file_path)
                self.lbl_text_img_path.configure(text=f"Kiválasztott kép: {os.path.basename(file_path)}")
                self.set_status(f"Kép betöltve: {os.path.basename(file_path)}")
                self.update_keys_from_images()
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba a kép betöltésekor: {e}")

    def select_base_image(self):
        file_path = filedialog.askopenfilename(
            title="Alapkép kiválasztása",
            filetypes=[("Kép fájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if file_path:
            try:
                self.base_image_path = file_path
                self.base_image = Image.open(file_path)
                self.lbl_base_path.configure(text=f"Alapkép: {os.path.basename(file_path)}")
                self.set_status(f"Alapkép betöltve: {os.path.basename(file_path)}")
                if not self.chk_sep_key_img_var.get():
                    self.key_image_img = self.base_image
                    self.key_image_path_img = file_path
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba az alapkép betöltésekor: {e}")

    def select_hidden_image(self):
        file_path = filedialog.askopenfilename(
            title="Rejtendő kép kiválasztása",
            filetypes=[("Kép fájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if file_path:
            try:
                self.hidden_image_path = file_path
                self.hidden_image = Image.open(file_path)
                self.lbl_hidden_path.configure(text=f"Rejtendő kép: {os.path.basename(file_path)}")
                self.set_status(f"Rejtendő kép betöltve: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba a rejtendő kép betöltésekor: {e}")

    def select_key_image(self):
        file_path = filedialog.askopenfilename(
            title="Kulcskép kiválasztása",
            filetypes=[("Kép fájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if file_path:
            try:
                self.key_image_path = file_path
                self.key_image = Image.open(file_path)
                self.lbl_text_key_path.configure(text=f"Kulcskép: {os.path.basename(file_path)}")
                self.set_status(f"Kulcskép betöltve: {os.path.basename(file_path)}")
                self.update_keys_from_images()
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba a kulcskép betöltésekor: {e}")

    def select_key_image_img(self):
        file_path = filedialog.askopenfilename(
            title="Kulcskép kiválasztása",
            filetypes=[("Kép fájlok", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if file_path:
            try:
                self.key_image_path_img = file_path
                self.key_image_img = Image.open(file_path)
                self.lbl_img_key_path.configure(text=f"Kulcskép: {os.path.basename(file_path)}")
                self.set_status(f"Kulcskép betöltve: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba a kulcskép betöltésekor: {e}")

    def update_keys_from_images(self):
        try:
            key_source_image = None
            if self.chk_sep_key_text_var.get() and self.key_image:
                key_source_image = self.key_image
            elif self.current_image:
                key_source_image = self.current_image
            if key_source_image:
                key64_bits = generate_64_bit_key_from_image(key_source_image)
                self.current_key64 = ''.join(str(bit) for bit in key64_bits)
                key256_bits = generate_256_bit_key_from_image(key_source_image)
                key256_hex = self.bits_to_hex(key256_bits)
                self.current_key256_hex = key256_hex.zfill(64)[:64]
                key_source = "kulcsképből" if self.chk_sep_key_text_var.get() else "a szöveg képéből"
                self.set_status(f"Kulcsok generálva {key_source}")
            else:
                self.current_key64 = None
                self.current_key256_hex = None
        except Exception as e:
            self.current_key64 = None
            self.current_key256_hex = None

    def get_image_key_hex(self) -> str or None:
        key_source = None
        if self.chk_sep_key_img_var.get() and self.key_image_img:
            key_source = self.key_image_img
        elif hasattr(self, 'base_image') and self.base_image:
            key_source = self.base_image
        if key_source is None: return None
        key256_bits = generate_256_bit_key_from_image(key_source)
        key256_hex = self.bits_to_hex(key256_bits)
        return key256_hex.zfill(64)[:64]

    def bits_to_hex(self, bits):
        hex_string = ''
        for i in range(0, len(bits), 4):
            if i+4 <= len(bits):
                nibble = bits[i:i+4]
                hex_string += hex(int(''.join(str(b) for b in nibble), 2))[2:]
        return hex_string

    # --- KATTINTÁSI METÓDUSOK ---

    def hide_text_new_image(self):
        if not self.current_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy képet a szöveghez!")
            return
        if not self.current_key64 or not self.current_key256_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsokat generálni!")
            return
        text = self.text_edit.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("Figyelmeztetés", "Írjon be szöveget az elrejtéshez!")
            return
        try:
            encrypted_text = aes_encrypt(text, self.current_key256_hex)
            text_bits = text_to_bits(encrypted_text)
            base, ext = os.path.splitext(self.current_image_path)
            output_path = f"{base}_hidden.png"
            embed_text_in_image(self.current_image_path, output_path, text_bits)
            self.set_status(f"Szöveg elrejtve: {os.path.basename(output_path)}")
            messagebox.showinfo("Siker", f"A szöveg sikeresen elrejtve!\nMentve: {output_path}")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba a szöveg elrejtésekor: {e}")

    def modify_image(self):
        if not self.current_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return
        if not self.current_key64 or not self.current_key256_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsokat generálni!")
            return
        text = self.text_edit.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("Figyelmeztetés", "Írjon be szöveget!")
            return
        if messagebox.askyesno('Megerősítés', 'Biztosan módosítani szeretné az eredeti képet?'):
            try:
                encrypted_text = aes_encrypt(text, self.current_key256_hex)
                text_bits = text_to_bits(encrypted_text)
                original_path = self.current_image_path
                new_path = original_path if os.path.splitext(original_path)[1].lower() == '.png' else os.path.splitext(original_path)[0] + '.png'
                embed_text_in_image(original_path, new_path, text_bits)
                if new_path != original_path:
                    os.remove(original_path)
                    self.current_image_path = new_path
                self.current_image = Image.open(self.current_image_path)
                self.set_status(f"Kép módosítva: {os.path.basename(self.current_image_path)}")
                messagebox.showinfo("Siker", "A kép sikeresen módosítva!")
            except Exception as e:
                messagebox.showerror("Hiba", f"Hiba a kép módosításakor: {e}")

    def extract_text(self):
        if not self.current_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return
        if not self.current_key64 or not self.current_key256_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült kulcsokat generálni!")
            return
        try:
            extracted_encrypted_text = extract_hidden_text_with_key(self.current_image)
            if not extracted_encrypted_text:
                messagebox.showwarning("Figyelmeztetés", "Nem található rejtett szöveg a képben!")
                return
            decrypted_text = aes_decrypt(extracted_encrypted_text, self.current_key256_hex)
            self.text_edit.delete("1.0", "end")
            self.text_edit.insert("1.0", decrypted_text)
            self.set_status("Szöveg sikeresen kinyerve!")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba a szöveg kinyerésekor: {e}")

    def copy_text(self):
        self.clipboard_clear()
        self.clipboard_append(self.text_edit.get("1.0", "end-1c").strip())
        self.set_status("Szöveg másolva")

    def hide_image(self):
        if not hasattr(self, 'base_image') or not self.base_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy alapképet!")
            return
        if not hasattr(self, 'hidden_image') or not self.hidden_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy rejtendő képet!")
            return
        if self.chk_sep_key_img_var.get() and not self.key_image_img:
            messagebox.showwarning("Figyelmeztetés", "Válasszon ki egy kulcsképet!")
            return
        key_hex = self.get_image_key_hex()
        if not key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült AES kulcsot generálni!")
            return
        try:
            encrypted_bits, resolution_bits, length_bits = hidden_image_to_bits(
                self.base_image_path, self.hidden_image_path, key_hex
            )
            base, ext = os.path.splitext(self.base_image_path)
            output_name = f"{base}_with_hidden.png"
            hidden_bits_to_image(self.base_image_path, output_name, encrypted_bits, resolution_bits, length_bits)
            self.set_status(f"Kép elrejtve: {os.path.basename(output_name)}")
            messagebox.showinfo("Siker", f"A kép sikeresen elrejtve!\nMentve: {output_name}")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba a kép elrejtésekor: {e}")

    def extract_image(self):
        if not hasattr(self, 'base_image') or not self.base_image:
            messagebox.showwarning("Figyelmeztetés", "Előbb válasszon ki egy alapképet!")
            return
        if self.chk_sep_key_img_var.get() and not self.key_image_img:
            messagebox.showwarning("Figyelmeztetés", "Válasszon ki egy kulcsképet!")
            return
        key_hex = self.get_image_key_hex()
        if not key_hex:
            messagebox.showwarning("Figyelmeztetés", "Nem sikerült AES kulcsot generálni!")
            return
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            extract_hidden_image(self.base_image_path, tmp_path, key_hex)
            
            # Preview (előnézeti) ablak beállítása
            preview_window = ctk.CTkToplevel(self)
            preview_window.title("Kinyert és visszafejtett kép")
            preview_window.geometry("550x550")
            preview_window.after(100, lambda: preview_window.focus())

            preview_img = Image.open(tmp_path)
            photo = ImageTk.PhotoImage(preview_img.resize((400, 400), Image.Resampling.LANCZOS))
            lbl_img = ctk.CTkLabel(preview_window, image=photo, text="")
            lbl_img.image = photo
            lbl_img.pack(pady=15, fill="both", expand=True)
            
            def save_extracted():
                save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG kép", "*.png")])
                if save_path:
                    shutil.copy(tmp_path, save_path)
                    self.set_status(f"Kép mentve: {os.path.basename(save_path)}")
                    messagebox.showinfo("Siker", f"Kép mentve:\n{save_path}", parent=preview_window)
            
            btn_save = ctk.CTkButton(preview_window, text="Kép mentése", command=save_extracted)
            btn_save.pack(pady=15)
            self.set_status("Kép sikeresen kinyerve.")
        except Exception as e:
            messagebox.showerror("Hiba", f"Hiba: {e}")


if __name__ == '__main__':
    app = SteganographyApp()
    app.mainloop()