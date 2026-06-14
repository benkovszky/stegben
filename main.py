import sys
import os
import base64
from PIL import Image
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                             QFileDialog, QMessageBox, QGroupBox, QCheckBox,
                             QTabWidget, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import math


#segédfüggvények
def zero_last_bit(r, g, b):
    r -= r % 2
    g -= g % 2
    b -= b % 2
    return r, g, b


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

def extraxt_interval(image):
    pixels = image.load()
    width, height = image.size
    #interval kinyerése
    interval_bits = ""
    for i in range(32):
        pixel = pixels[width - 1, height - 1 -i]
        interval_bits += str(pixel[0] & 1)
    interval = int(interval_bits, 2)
    print(f"Kinyert intervallum: {interval}")
    return interval


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

def embed_text_in_image(image_path, output_path, binary_text):
    img = Image.open(image_path).convert('RGB')
    pixels = img.load()
    width, height = img.size
    interval = int(((width * height)- 200) // len(binary_text))

    #interval egésszé alakítása a float hiba elkerüléséhez
    interval_bits = format(interval & 0xFFFFFFFF, '032b')
    for i in range(32):
        x, y = width - 1, height - 1 - i
        pixel = list(pixels[x, y])
        pixel[0] = (pixel[0] & ~1) | int(interval_bits[i])
        pixels[x, y] = tuple(pixel)   # visszaírás

    hidden_length = len(binary_text) * interval
    print("az interval értéke: ", interval)
    print("Elrejtett adat hossza: ", hidden_length)


    validation_list = create_validation_list(img, hidden_length, interval)

    x_position = 14
    y_position = 88
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









#szöveg kinyerése
def extract_hidden_text_with_key(image):
    pixels = image.load()
    width, height = image.size
    
    interval = extraxt_interval(image)
    hidden_length = search_64_bit_key(image)
    validation_data = create_validation_list(image, hidden_length, interval)


    extracted_binary = [0] * (hidden_length // interval)

    x_position = 14
    y_position = 88
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

    # felbontás és hossz visszaalakítása
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


    """
    ======================================================================================================================================================================
    =========================================================itt kezdődik a gui===========================================================================================
    ======================================================================================================================================================================
    """

class SteganographyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self.current_image = None
        self.key_image_path = None
        self.key_image = None
        self.hidden_image_path = None
        self.hidden_image = None
        self.current_key64 = None
        self.current_key256_hex = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Digitális szteganográfia Alkalmazás')
        self.setGeometry(100, 100, 900, 700)
        
        # Központi widget és tabok
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tab widget létrehozása
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Szöveg tab
        text_tab = QWidget()
        self.setup_text_tab(text_tab)
        tabs.addTab(text_tab, "Szöveg elrejtése/kinyerése")
        
        # Kép tab
        image_tab = QWidget()
        self.setup_image_tab(image_tab)
        tabs.addTab(image_tab, "Kép elrejtése/kinyerése")
        
        # Státusz sor
        self.status_label = QLabel("Kész")
        main_layout.addWidget(self.status_label)
        
    def setup_text_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Kép kiválasztás a szöveghez
        image_group = QGroupBox("Kép a szöveg elrejtéséhez")
        image_layout = QHBoxLayout()
        
        self.image_path_label = QLabel("Nincs kép kiválasztva")
        self.image_path_label.setWordWrap(True)
        
        select_image_btn = QPushButton("Kép kiválasztása")
        select_image_btn.clicked.connect(self.select_image)
        
        image_layout.addWidget(self.image_path_label)
        image_layout.addWidget(select_image_btn)
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)
        
        # Külön kulcskép opció
        key_checkbox_layout = QHBoxLayout()
        self.use_separate_key_image = QCheckBox("Külön kép használata a kulcsokhoz")
        self.use_separate_key_image.stateChanged.connect(self.toggle_key_image_selection)
        key_checkbox_layout.addWidget(self.use_separate_key_image)
        key_checkbox_layout.addStretch()
        layout.addLayout(key_checkbox_layout)
        
        # Külön kulcskép kiválasztás
        self.key_image_group = QGroupBox("Kulcskép kiválasztása")
        self.key_image_group.setEnabled(False)
        key_image_layout = QHBoxLayout()
        
        self.key_image_path_label = QLabel("Nincs kulcskép kiválasztva")
        self.key_image_path_label.setWordWrap(True)
        
        select_key_image_btn = QPushButton("Kulcskép kiválasztása")
        select_key_image_btn.clicked.connect(self.select_key_image)
        
        key_image_layout.addWidget(self.key_image_path_label)
        key_image_layout.addWidget(select_key_image_btn)
        self.key_image_group.setLayout(key_image_layout)
        layout.addWidget(self.key_image_group)
        
        # Szöveg szerkesztő
        text_group = QGroupBox("Szöveg")
        text_layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Ide írja a rejtendő szöveget...")
        text_layout.addWidget(self.text_edit)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # Műveletek szöveghez
        text_actions_group = QGroupBox("Műveletek szöveggel")
        text_actions_layout = QHBoxLayout()
        
        hide_new_btn = QPushButton("Elrejtés (új kép)")
        hide_new_btn.clicked.connect(self.hide_text_new_image)
        
        modify_btn = QPushButton("Módosítás")
        modify_btn.clicked.connect(self.modify_image)
        
        extract_btn = QPushButton("Kinyerés")
        extract_btn.clicked.connect(self.extract_text)
        
        copy_btn = QPushButton("Szöveg másolása")
        copy_btn.clicked.connect(self.copy_text)
        
        text_actions_layout.addWidget(hide_new_btn)
        text_actions_layout.addWidget(modify_btn)
        text_actions_layout.addWidget(extract_btn)
        text_actions_layout.addWidget(copy_btn)
        text_actions_group.setLayout(text_actions_layout)
        layout.addWidget(text_actions_group)
        
        layout.addStretch()
    
    def setup_image_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Alapkép kiválasztás
        base_image_group = QGroupBox("Alapkép (ahová rejtünk)")
        base_image_layout = QHBoxLayout()
        
        self.base_image_path_label = QLabel("Nincs alapkép kiválasztva")
        self.base_image_path_label.setWordWrap(True)
        
        select_base_image_btn = QPushButton("Alapkép kiválasztása")
        select_base_image_btn.clicked.connect(self.select_base_image)
        
        base_image_layout.addWidget(self.base_image_path_label)
        base_image_layout.addWidget(select_base_image_btn)
        base_image_group.setLayout(base_image_layout)
        layout.addWidget(base_image_group)
        
        # Rejtendő kép kiválasztás
        hidden_image_group = QGroupBox("Rejtendő kép")
        hidden_image_layout = QHBoxLayout()
        
        self.hidden_image_path_label = QLabel("Nincs rejtendő kép kiválasztva")
        self.hidden_image_path_label.setWordWrap(True)
        
        select_hidden_image_btn = QPushButton("Rejtendő kép kiválasztása")
        select_hidden_image_btn.clicked.connect(self.select_hidden_image)
        
        hidden_image_layout.addWidget(self.hidden_image_path_label)
        hidden_image_layout.addWidget(select_hidden_image_btn)
        hidden_image_group.setLayout(hidden_image_layout)
        layout.addWidget(hidden_image_group)
        
        # Külön kulcskép opció képekhez
        key_checkbox_layout_img = QHBoxLayout()
        self.use_separate_key_image_img = QCheckBox("Külön kép használata a kulcsokhoz")
        self.use_separate_key_image_img.stateChanged.connect(self.toggle_key_image_selection_img)
        key_checkbox_layout_img.addWidget(self.use_separate_key_image_img)
        key_checkbox_layout_img.addStretch()
        layout.addLayout(key_checkbox_layout_img)
        
        # Külön kulcskép kiválasztás képekhez
        self.key_image_group_img = QGroupBox("Kulcskép kiválasztása")
        self.key_image_group_img.setEnabled(False)
        key_image_layout_img = QHBoxLayout()
        
        self.key_image_path_label_img = QLabel("Nincs kulcskép kiválasztva")
        self.key_image_path_label_img.setWordWrap(True)
        
        select_key_image_img_btn = QPushButton("Kulcskép kiválasztása")
        select_key_image_img_btn.clicked.connect(self.select_key_image_img)
        
        key_image_layout_img.addWidget(self.key_image_path_label_img)
        key_image_layout_img.addWidget(select_key_image_img_btn)
        self.key_image_group_img.setLayout(key_image_layout_img)
        layout.addWidget(self.key_image_group_img)
        
        # Kimeneti fájl név
        output_layout = QHBoxLayout()       
        self.image_output_name = QLineEdit()
        output_layout.addWidget(self.image_output_name)
        layout.addLayout(output_layout)
        
        # Műveletek képhez
        image_actions_group = QGroupBox("Műveletek képpel")
        image_actions_layout = QHBoxLayout()
        
        hide_image_btn = QPushButton("Kép elrejtése")
        hide_image_btn.clicked.connect(self.hide_image)
        
        extract_image_btn = QPushButton("Kép kinyerése")
        extract_image_btn.clicked.connect(self.extract_image)
        
        image_actions_layout.addWidget(hide_image_btn)
        image_actions_layout.addWidget(extract_image_btn)
        image_actions_group.setLayout(image_actions_layout)
        layout.addWidget(image_actions_group)
        
        layout.addStretch()
    
    def toggle_key_image_selection(self, state):
        self.key_image_group.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.key_image_path = None
            self.key_image = None
            self.update_keys_from_images()
    
    def toggle_key_image_selection_img(self, state):
        self.key_image_group_img.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.key_image_path = None
            self.key_image = None
        
    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Kép kiválasztása a szöveghez", "", 
            "Kép fájlok (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            try:
                self.current_image_path = file_path
                self.current_image = Image.open(file_path)
                self.image_path_label.setText(f"Kiválasztott kép: {os.path.basename(file_path)}")
                self.status_label.setText(f"Kép betöltve: {os.path.basename(file_path)}")
                self.update_keys_from_images()
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba a kép betöltésekor: {e}")
    
    def select_base_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Alapkép kiválasztása", "", 
            "Kép fájlok (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            try:
                self.base_image_path = file_path
                self.base_image = Image.open(file_path)
                self.base_image_path_label.setText(f"Alapkép: {os.path.basename(file_path)}")
                self.status_label.setText(f"Alapkép betöltve: {os.path.basename(file_path)}")
                
                if not self.use_separate_key_image_img.isChecked():
                    self.key_image = self.base_image
                    self.key_image_path = file_path
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba az alapkép betöltésekor: {e}")
    
    def select_hidden_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Rejtendő kép kiválasztása", "", 
            "Kép fájlok (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            try:
                self.hidden_image_path = file_path
                self.hidden_image = Image.open(file_path)
                self.hidden_image_path_label.setText(f"Rejtendő kép: {os.path.basename(file_path)}")
                self.status_label.setText(f"Rejtendő kép betöltve: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba a rejtendő kép betöltésekor: {e}")
    
    def select_key_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Kulcskép kiválasztása", "", 
            "Kép fájlok (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            try:
                self.key_image_path = file_path
                self.key_image = Image.open(file_path)
                self.key_image_path_label.setText(f"Kulcskép: {os.path.basename(file_path)}")
                self.status_label.setText(f"Kulcskép betöltve: {os.path.basename(file_path)}")
                self.update_keys_from_images()
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba a kulcskép betöltésekor: {e}")
    
    def select_key_image_img(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Kulcskép kiválasztása", "", 
            "Kép fájlok (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            try:
                self.key_image_path_img = file_path
                self.key_image = Image.open(file_path)
                self.key_image_path_label_img.setText(f"Kulcskép: {os.path.basename(file_path)}")
                self.status_label.setText(f"Kulcskép betöltve: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba a kulcskép betöltésekor: {e}")
    
    def update_keys_from_images(self):
        try:
            key_source_image = None
            
            if self.use_separate_key_image.isChecked() and self.key_image:
                key_source_image = self.key_image
            elif self.current_image:
                key_source_image = self.current_image
            
            if key_source_image:
                key64_bits = generate_64_bit_key_from_image(key_source_image)
                self.current_key64 = ''.join(str(bit) for bit in key64_bits)
                
                key256_bits = generate_256_bit_key_from_image(key_source_image)
                key256_hex = self.bits_to_hex(key256_bits)
                self.current_key256_hex = key256_hex.zfill(64)[:64]
                
                key_source = "kulcsképből" if self.use_separate_key_image.isChecked() else "a szöveg képéből"
                self.status_label.setText(f"Kulcsok generálva {key_source}")
            else:
                self.current_key64 = None
                self.current_key256_hex = None
                
        except Exception as e:
            print(f"Hiba a kulcsok frissítésekor: {e}")
            self.current_key64 = None
            self.current_key256_hex = None

    def get_image_key_hex(self) -> str | None:
        """
        Visszaadja a képtitkosításhoz használandó 256-bites AES kulcsot hex-ben.
        Ha külön kulcskép van kiválasztva, abból generál, egyébként az alapképből.
        """
        key_source = None
        if self.use_separate_key_image_img.isChecked() and self.key_image:
            key_source = self.key_image
        elif hasattr(self, 'base_image') and self.base_image:
            key_source = self.base_image

        if key_source is None:
            return None

        key256_bits = generate_256_bit_key_from_image(key_source)
        key256_hex = self.bits_to_hex(key256_bits)
        return key256_hex.zfill(64)[:64]
    
    def bits_to_hex(self, bits):
        hex_string = ''
        for i in range(0, len(bits), 4):
            if i+4 <= len(bits):
                nibble = bits[i:i+4]
                hex_digit = hex(int(''.join(str(b) for b in nibble), 2))[2:]
                hex_string += hex_digit
        return hex_string
    
    def hide_text_new_image(self):
        if not self.current_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Előbb válasszon ki egy képet a szöveghez!")
            return
        
        if not self.current_key64 or not self.current_key256_hex:
            QMessageBox.warning(self, "Figyelmeztetés", "Nem sikerült kulcsokat generálni! Ellenőrizze a kép(ek)et!")
            return
        
        text = self.text_edit.toPlainText()
        if not text:
            QMessageBox.warning(self, "Figyelmeztetés", "Írjon be szöveget az elrejtéshez!")
            return
        
        try:
            # Szöveg titkosítása
            encrypted_text = aes_encrypt(text, self.current_key256_hex)
            # Szöveg átalakítása bitekké
            text_bits = text_to_bits(encrypted_text)
            base, ext = os.path.splitext(self.current_image_path)
            output_path = f"{base}_hidden.png"
            # Szöveg elrejtése + kulcs hozzáfűzése
            embed_text_in_image(self.current_image_path, output_path, text_bits)
            self.status_label.setText(f"Szöveg elrejtve: {os.path.basename(output_path)}")
            QMessageBox.information(self, "Siker", f"A szöveg sikeresen elrejtve!\nMentve: {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Hiba a szöveg elrejtésekor: {e}")
    
    def modify_image(self):
        if not self.current_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return

        if not self.current_key64 or not self.current_key256_hex:
            QMessageBox.warning(self, "Figyelmeztetés", "Nem sikerült kulcsokat generálni! Ellenőrizze a kép(ek)et!")
            return

        text = self.text_edit.toPlainText()
        if not text:
            QMessageBox.warning(self, "Figyelmeztetés", "Írjon be szöveget az elrejtéshez!")
            return

        reply = QMessageBox.question(self, 'Megerősítés', 
                                    'Biztosan módosítani szeretné az eredeti képet?',
                                    QMessageBox.Yes | QMessageBox.No, 
                                    QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # Szöveg titkosítása
                encrypted_text = aes_encrypt(text, self.current_key256_hex)
                # Szöveg átalakítása bitekké
                text_bits = text_to_bits(encrypted_text)

                original_path = self.current_image_path
                file_ext = os.path.splitext(original_path)[1].lower()

                # Ha nem PNG, akkor az új mentési útvonal .png legyen
                if file_ext != '.png':
                    new_path = os.path.splitext(original_path)[0] + '.png'
                else:
                    new_path = original_path  # PNG esetén felülírjuk az eredetit

                # Szöveg elrejtése a képbe (input: original_path, output: new_path)
                embed_text_in_image(original_path, new_path, text_bits)

                # Ha új fájlt hoztunk létre (nem PNG eredeti), töröljük az eredetit
                if new_path != original_path:
                    os.remove(original_path)
                    self.current_image_path = new_path

                # Kép újratöltése
                self.current_image = Image.open(self.current_image_path)
                self.status_label.setText(f"Kép módosítva: {os.path.basename(self.current_image_path)}")
                QMessageBox.information(self, "Siker", "A kép sikeresen módosítva!")

            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Hiba a kép módosításakor: {e}")
    
    def extract_text(self):
        if not self.current_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Előbb válasszon ki egy képet!")
            return
        
        if not self.current_key64 or not self.current_key256_hex:
            QMessageBox.warning(self, "Figyelmeztetés", "Nem sikerült kulcsokat generálni! Ellenőrizze a kép(ek)et!")
            return
        
        try:
            # Rejtett szöveg kinyerése
            extracted_encrypted_text = extract_hidden_text_with_key(self.current_image)
            
            if not extracted_encrypted_text:
                QMessageBox.warning(self, "Figyelmeztetés", "Nem található rejtett szöveg a képben!")
                return
            
            # Szöveg visszafejtése
            decrypted_text = aes_decrypt(extracted_encrypted_text, self.current_key256_hex)
            # Szöveg megjelenítése
            self.text_edit.setText(decrypted_text)
            self.status_label.setText("Szöveg sikeresen kinyerve és visszafejtve!")
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Hiba a szöveg kinyerésekor: {e}")
    
    def hide_image(self):
        if not hasattr(self, 'base_image') or not self.base_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Előbb válasszon ki egy alapképet!")
            return
        
        if not hasattr(self, 'hidden_image') or not self.hidden_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Előbb válasszon ki egy rejtendő képet!")
            return
        
        # Kulcskép ellenőrzése
        if self.use_separate_key_image_img.isChecked() and not self.key_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Válasszon ki egy kulcsképet!")
            return
        
        key_hex = self.get_image_key_hex()
        if not key_hex:
            QMessageBox.warning(self, "Figyelmeztetés", "Nem sikerült AES kulcsot generálni a képhez!")
            return
        
        try:
            # Rejtett kép bitekké alakítása és titkosítása
            encrypted_bits, resolution_bits, length_bits = hidden_image_to_bits(
                self.base_image_path, self.hidden_image_path, key_hex
            )
            
            # Kimeneti fájlnév
            output_name = self.image_output_name.text().strip()
            if not output_name:
                base, ext = os.path.splitext(self.base_image_path)
                output_name = f"{base}_with_hidden.png"
            else:
                # Biztosítsuk, hogy a megfelelő kiterjesztés legyen
                if not output_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                    output_name += '.png'
                output_name = os.path.join(os.path.dirname(self.base_image_path), output_name)
            
            # Titkosított kép elrejtése
            hidden_bits_to_image(
                self.base_image_path, output_name,
                encrypted_bits, resolution_bits, length_bits
            )
            
            self.status_label.setText(f"Titkosított kép elrejtve: {os.path.basename(output_name)}")
            QMessageBox.information(self, "Siker", 
                f"A kép AES-256 titkosítással sikeresen elrejtve!\nMentve: {output_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Hiba a kép elrejtésekor: {e}")
    
    def extract_image(self):
        if not hasattr(self, 'base_image') or not self.base_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Előbb válasszon ki egy alapképet, amely tartalmazza a rejtett képet!")
            return
        
        # Kulcskép ellenőrzése
        if self.use_separate_key_image_img.isChecked() and not self.key_image:
            QMessageBox.warning(self, "Figyelmeztetés", "Válasszon ki egy kulcsképet a visszafejtéshez!")
            return
        
        key_hex = self.get_image_key_hex()
        if not key_hex:
            QMessageBox.warning(self, "Figyelmeztetés", "Nem sikerült AES kulcsot generálni a visszafejtéshez!")
            return
        
        try:
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
            
            # Titkosított kép kinyerése és visszafejtése
            extract_hidden_image(self.base_image_path, tmp_path, key_hex)
            
            # Előnézeti ablak megnyitása
            self.preview_window = QWidget()
            self.preview_window.setWindowTitle("Kinyert és visszafejtett kép")
            self.preview_window.setMinimumSize(400, 400)
            preview_layout = QVBoxLayout(self.preview_window)
            
            # Kép megjelenítése
            image_label = QLabel()
            pixmap = QPixmap(tmp_path)
            pixmap = pixmap.scaled(600, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            preview_layout.addWidget(image_label)
            
            # Mentés gomb
            def save_image():
                save_path, _ = QFileDialog.getSaveFileName(
                    self.preview_window, "Kép mentése", "kinyert_kep.png",
                    "Kép fájlok (*.png *.jpg *.jpeg *.bmp *.tiff)"
                )
                if save_path:
                    import shutil
                    shutil.copy(tmp_path, save_path)
                    self.status_label.setText(f"Kép mentve: {os.path.basename(save_path)}")
                    QMessageBox.information(self.preview_window, "Siker", f"Kép mentve:\n{save_path}")
            
            save_btn = QPushButton("Mentés")
            save_btn.clicked.connect(save_image)
            preview_layout.addWidget(save_btn)
            
            self.preview_window.show()
            self.status_label.setText("Titkosított rejtett kép sikeresen kinyerve és visszafejtve")
        
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Hiba a kép kinyerésekor/visszafejtésekor: {e}")
    
    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        self.status_label.setText("Szöveg másolva")

def main():
    app = QApplication(sys.argv)
    window = SteganographyApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()