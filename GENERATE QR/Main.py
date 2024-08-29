import json
import logging
import os
import string
import textwrap
import random
import datetime
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class QRCodeGenerator:
    def __init__(self):
        self.generated_image_path = None

    def generate_alphanumeric(self, length=7):
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(length - 4))
        result = f"2K24{random_string}"
        logging.debug(f"Generated alphanumeric string: {result}")
        return result

    def load_registry(self, registry_file):
        if os.path.exists(registry_file):
            try:
                with open(registry_file, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                logging.error("Failed to decode JSON from the registry file.")
            except IOError as e:
                logging.error(f"IOError while reading the registry file: {e}")
        return {}

    def save_registry(self, registry, registry_file):
        try:
            with open(registry_file, 'w') as file:
                json.dump(registry, file, indent=4)
        except IOError as e:
            logging.error(f"Failed to save registry: {e}")

    def is_code_unique(self, code, registry):
        return code not in registry

    def generate_code_for_db(self):
        REGISTRY_FILE = 'code_registry.json'
        registry = self.load_registry(REGISTRY_FILE)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        src = r"C:\Users\bornd\Downloads\Onam.csv"
        data = pd.read_csv(src)
        data_cleaned = data.dropna()
        logging.debug(f"Null values after cleaning: {data_cleaned.isnull().sum()}")

        os.makedirs('temp', exist_ok=True)

        for index, row in data_cleaned.iterrows():
            # Generate unique number
            unique_number = self.generate_alphanumeric()
            while not self.is_code_unique(unique_number, registry):
                unique_number = self.generate_alphanumeric()

            full_string = f"{unique_number}"
            logging.debug(f"Generating QR code with data: {full_string} for {row['CODE']}")

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

            draw = ImageDraw.Draw(background_image)
            name_pos = (1090, 150)
            name_font = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 20)
            draw.text(name_pos, "", fill="black", font=name_font)

            name_font_large = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 40)
            wrapped_name = textwrap.fill(row['Name'], width=14)
            name_lines = wrapped_name.split('\n')

            for i, line in enumerate(name_lines):
                actual_name_pos = (1050, 200 + i * 50)
                draw.text(actual_name_pos, line, fill="black", font=name_font_large)

            img_2 = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
            unique_number_font = ImageFont.truetype("FontsFree-Net-Disket-Mono-Bold.ttf", 45)
            draw = ImageDraw.Draw(img_2)

            unique_number_position = (10, 10)
            draw.text(unique_number_position, f"{unique_number}", fill="black", font=unique_number_font)
            img_2 = img_2.rotate(90, expand=True, fillcolor=(255, 255, 255, 0))

            background_image.paste(img_2, (1600, 150), img_2)

            email_part = row['CODE'].split('@')[0]
            image_path = f"temp/{email_part}.png"

            try:
                background_image.save(image_path)
                self.generated_image_path = image_path
                logging.info(f"QR code combined with ticket, name, and unique number saved to {image_path}")

                timestamp = datetime.datetime.now().isoformat()
                registry[unique_number] = {
                    'unique_value': unique_number,
                    'ID': row['CODE'],
                    'name': row['Name'],
                    'generated_time': timestamp,
                    'mail': row[' Mail ID'],
                    'attendance': False,
                    'entry_time': None
                }
                self.save_registry(registry, REGISTRY_FILE)
            except IOError as e:
                logging.error(f"Failed to save image for {row['Name']}: {e}")
                continue

            qr.clear()

        # Insert the data into the database
        self.insert_qr_codes_to_db(REGISTRY_FILE)

    def insert_qr_codes_to_db(self, data_path):
        load_dotenv()
        driver = os.getenv("DB_DRIVER")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_cluster = os.getenv("DB_CLUSTER")

        db_string = f"{driver}://{db_user}:{db_password}@{db_cluster}"
        client = MongoClient(db_string)
        db = client['reflections']
        collection = db['qr_codes']

        try:
            with open(data_path, 'r') as file:
                data = json.load(file)

            emp_list = [value for key, value in data.items()]
            collection.insert_many(emp_list)
            logging.info("Insertion successful into MongoDB")
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Failed to load or insert data into MongoDB: {e}")
        except Exception as e:
            logging.error(f"An error occurred during MongoDB insertion: {e}")


# Sample code to run the generator
if __name__ == "__main__":
    generator = QRCodeGenerator()
    generator.generate_code_for_db()
    # generator.insert_qr_codes_to_db("./code_registry.json")
