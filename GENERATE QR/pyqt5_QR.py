import json
import logging
import os
import random
import string
import cv2
import qrcode
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtGui
from PIL import Image, ImageDraw, ImageFont
import qrcode.constants
import textwrap
import pandas as pd

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('application.log'),
        logging.StreamHandler()
    ]
)


class MyGUI(QMainWindow):
    def __init__(self):
        super(MyGUI, self).__init__()
        uic.loadUi("code_gen.ui", self)
        self.setFixedSize(600, 350)
        self.show()
        self.current_file = ""
        self.generated_image_path = None

        self.actionLoad.triggered.connect(self.load_image)
        self.qr_to_text.clicked.connect(self.read_code)
        self.text_to_qr.clicked.connect(self.generate_code)
        self.save.clicked.connect(self.generate_code_for_db)

        logging.info("Application started")

    def generate_alphanumeric(self, length=7):
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(length - 4))
        result = f"2K24{random_string}"
        logging.debug(f"Generated alphanumeric string: {result}")
        return result

    def load_image(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*)", options=options)

        if filename != "":
            self.current_file = filename
            pixmap = QtGui.QPixmap(self.current_file)
            pixmap = pixmap.scaled(300, 300)
            self.label.setScaledContents(True)
            self.label.setPixmap(pixmap)
            logging.info(f"Loaded image file: {filename}")
        else:
            logging.warning("No file selected")

    def read_code(self):
        image = cv2.imread(self.current_file)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image)

        if data:
            self.name.setText(data)
            logging.info(f"QR code data read: {data}")
        else:
            self.name.setText("No QR Selected !!!!")
            logging.warning("No QR code detected in the image")

    def generate_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        name = self.name.toPlainText()
        email = self.email.toPlainText()
        unique_number = self.generate_alphanumeric()

        full_string = f"{name} {email} {unique_number}"
        logging.debug(f"Generating QR code with data: {full_string}")

        qr.add_data(full_string)
        qr.make(fit=True)
        back_color = (110, 189, 70)
        qr_image = qr.make_image(fill_color='black', back_color=back_color).convert('RGBA')
        qr_image = qr_image.resize((350, 350))

        background_image = Image.open('OnamPassTicket.jpg').convert('RGBA')

        qr_position = (120, 150)
        background_image.paste(qr_image, qr_position, qr_image)

        draw = ImageDraw.Draw(background_image)

        name_pos = (1090, 150)
        name_font = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 20)
        draw.text(name_pos, "Name:", fill="black", font=name_font)

        name_font_large = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 40)
        wrapped_name = textwrap.fill(name, width=12)
        name_lines = wrapped_name.split('\n')

        for i, line in enumerate(name_lines):
            actual_name_pos = (1090, 200 + i * 50)
            draw.text(actual_name_pos, line, fill="black", font=name_font_large)

        img_2 = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
        unique_number_font = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 45)
        draw = ImageDraw.Draw(img_2)

        unique_number_position = (10, 10)
        draw.text(unique_number_position, f"{unique_number}", fill="black", font=unique_number_font)
        img_2 = img_2.rotate(90, expand=True, fillcolor=(255, 255, 255, 0))

        background_image.paste(img_2, (1600, 180), img_2)

        image_path = f"temp/{email}_ticket.png"
        background_image.save(image_path)
        self.generated_image_path = image_path

        pixmap = QtGui.QPixmap(image_path)
        pixmap = pixmap.scaled(300, 300)
        self.label.setScaledContents(True)
        self.label.setPixmap(pixmap)
        logging.info(f"QR code combined with ticket, name, and unique number saved to {image_path}")

    def save_image(self):
        if self.generated_image_path:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "PNG Files (*.png); All Files (*)")
            if save_path:
                try:
                    with open(self.generated_image_path, 'rb') as src_file:
                        with open(save_path, 'wb') as dest_file:
                            dest_file.write(src_file.read())
                    logging.info(f"QR code image saved to {save_path}")
                except IOError as e:
                    logging.error(f"Failed to save QR code image: {e}")
        else:
            logging.warning("No QR code image to save")

    def generate_code_for_db(self):
        REGISTRY_FILE = 'code_registry.json'

        def load_registry():
            if os.path.exists(REGISTRY_FILE):
                with open(REGISTRY_FILE, 'r') as file:
                    return json.load(file)
            return {}

        def save_registry(registry):
            with open(REGISTRY_FILE, 'w') as file:
                json.dump(registry, file, indent=4)

        def is_code_unique(code, registry):
            return code not in registry

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        src = r"C:\Users\bornd\Downloads\Onam.csv"
        data = pd.read_csv(src)
        data_cleaned = data.dropna()
        print(data_cleaned.isnull().sum())

        os.makedirs('temp', exist_ok=True)

        # Load existing registry
        registry = load_registry()

        # Process each entry in the DataFrame
        for index, row in data_cleaned.iterrows():
            # Generate unique number and check its uniqueness
            while True:
                unique_number = self.generate_alphanumeric()
                if is_code_unique(unique_number, registry):
                    break

            full_string = f"{unique_number}"
            logging.debug(f"Generating QR code with data: {full_string} for {row['CODE']}")

            # Generate QR code
            qr.add_data(full_string)
            qr.make(fit=True)
            back_color = (110, 189, 70)
            qr_image = qr.make_image(fill_color='black', back_color=back_color).convert('RGBA')
            qr_image = qr_image.resize((350, 350))

            try:
                background_image = Image.open('OnamPassTicket.jpg').convert('RGBA')
            except IOError:
                logging.error("Failed to open background image.")
                continue

            qr_position = (120, 150)
            background_image.paste(qr_image, qr_position, qr_image)

            # Add name to the image
            draw = ImageDraw.Draw(background_image)
            name_pos = (1090, 150)
            name_font = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 20)
            draw.text(name_pos, "Name:", fill="black", font=name_font)

            name_font_large = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 40)
            wrapped_name = textwrap.fill(row['Name'], width=12)
            name_lines = wrapped_name.split('\n')

            for i, line in enumerate(name_lines):
                actual_name_pos = (1090, 200 + i * 50)
                draw.text(actual_name_pos, line, fill="black", font=name_font_large)

            # Add unique number as an image rotated 90 degrees
            img_2 = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
            unique_number_font = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 45)
            draw = ImageDraw.Draw(img_2)

            unique_number_position = (10, 10)
            draw.text(unique_number_position, f"{unique_number}", fill="black", font=unique_number_font)
            img_2 = img_2.rotate(90, expand=True, fillcolor=(255, 255, 255, 0))

            background_image.paste(img_2, (1600, 120), img_2)

            email_part = row['CODE'].split('@')[0]
            image_path = f"temp/{email_part}.png"

            try:
                background_image.save(image_path)
                self.generated_image_path = image_path
                logging.info(f"QR code combined with ticket, name, and unique number saved to {image_path}")

                # Update the registry
                registry[unique_number] = image_path
                save_registry(registry)
            except IOError as e:
                logging.error(f"Failed to save image for {row['Name']}: {e}")
                continue

            # Update the QLabel in the GUI
            pixmap = QtGui.QPixmap(image_path)
            pixmap = pixmap.scaled(300, 300)
            self.label.setScaledContents(True)
            self.label.setPixmap(pixmap)
            qr.clear()


def main():
    app = QApplication([])
    window = MyGUI()

    app.exec_()


if __name__ == "__main__":
    main()
