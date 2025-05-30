import os
import re
import cv2
import json
import pytesseract
import logging
import tempfile
import requests
import certifi
import urllib3
import numpy as np
from flask import Flask, request, jsonify
from datetime import datetime
from pdf2image import convert_from_path
from fuzzywuzzy import fuzz

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

app = Flask(__name__)

class AadhaarExtractor:
    def __init__(self, dpi=300, max_lines=10):
        self.dpi = dpi
        self.max_lines = max_lines

    def preprocess_image(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def image_from_pdf(self, pdf_path, page_num=0):
        images = convert_from_path(pdf_path, dpi=self.dpi)
        return np.array(images[page_num])

    def extract_text(self, image):
        preprocessed = self.preprocess_image(image)
        return pytesseract.image_to_string(preprocessed, lang="eng")

    def clean_line(self, line):
        return re.sub(r"^[^A-Za-z]+", "", line).strip()

    def clean_name(self, name):
        name = re.sub(r"^[^\w]*", "", name)
        name = re.sub(r"^(y\s*\.\s*)", "", name, flags=re.I)
        name = re.sub(r"^(mr\.?|ms\.?|mrs\.?)\s+", "", name, flags=re.I)
        return name.strip()

    def extract_name(self, lines):
        for line in lines[:self.max_lines]:
            cleaned = self.clean_line(line)
            if any(kw in cleaned.lower() for kw in [
                'dob', 'birth', 'male', 'female', 'year', 'uidai', 'issue', 'government', 'india']):
                continue
            if re.search(r"[A-Za-z]{2,}", cleaned):
                return self.clean_name(cleaned)
        return ""

    def extract_aadhaar_info(self, text):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        name_en = self.extract_name(lines)
        dob = gender = aadhaar_number = ""

        for line in lines:
            lline = line.lower()
            if fuzz.partial_ratio(lline, "male") > 80:
                gender = "Male"
            elif fuzz.partial_ratio(lline, "female") > 80:
                gender = "Female"
            elif fuzz.partial_ratio(lline, "transgender") > 80:
                gender = "Transgender"

            # Aadhaar number: take only 12 consecutive digits from a line
            digits_only = re.sub(r"\D", "", line)
            if len(digits_only) == 12 and not aadhaar_number:
                aadhaar_number = digits_only

            dob_match = re.search(
                r"(?:DOB|DoB|D0B|Year of Birth|Birth Year)?[^\d]*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4})",
                line, re.IGNORECASE
            )
            if dob_match and not dob:
                raw_dob = dob_match.group(1)
                try:
                    if re.match(r"\d{2}[/-]\d{2}[/-]\d{4}", raw_dob):
                        dob = datetime.strptime(raw_dob.replace("/", "-"), "%d-%m-%Y").strftime("%d-%b-%Y")
                    else:
                        dob = raw_dob
                except ValueError:
                    dob = raw_dob

        if not dob:
            for line in lines:
                year_only = re.search(r"\b(19|20)\d{2}\b", line)
                if year_only:
                    dob = year_only.group(0)
                    break

        return {
            "Name": name_en,
            "Gender": gender,
            "DOB/Year of Birth": dob,
            "Aadhaar Number": aadhaar_number
        }

    def download_pdf_from_url(self, url):
        try:
            response = requests.get(url, verify=certifi.where(), timeout=10)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            response = requests.get(url, verify=False, timeout=10)
        except Exception as e:
            raise Exception(f"Secure download failed: {e}")

        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.write(response.content)
            temp_file.close()
            return temp_file.name
        else:
            raise Exception(f"Failed to download file from URL: HTTP {response.status_code}")

    def extract_from_file(self, file_path_or_url):
        temp_pdf_path = None
        try:
            if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
                temp_pdf_path = self.download_pdf_from_url(file_path_or_url)
                file_path = temp_pdf_path
            else:
                file_path = file_path_or_url

            image = self.image_from_pdf(file_path)
            text = self.extract_text(image)
            info = self.extract_aadhaar_info(text)
            return info
        except Exception as e:
            logging.error(f"Extraction failed: {e}")
            return {
                "Name": "", "Gender": "", "DOB/Year of Birth": "", "Aadhaar Number": ""
            }
        finally:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

extractor = AadhaarExtractor()

@app.route("/extract-aadhaar", methods=["POST"])
def extract_aadhaar():
    logging.info("API called /extract-aadhaar")
    try:
        data = request.get_json()
        pdf_url = data.get("pdf_url")
        if not pdf_url:
            return jsonify({"error": "pdf_url is required in JSON body"}), 400

        result = extractor.extract_from_file(pdf_url)
        return jsonify(result)
    except Exception as e:
        logging.error(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
