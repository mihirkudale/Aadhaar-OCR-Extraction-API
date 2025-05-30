# Aadhaar OCR Extraction API

This Flask API extracts Aadhaar details (Name, Gender, DOB, Aadhaar Number) from an Aadhaar PDF file URL using Tesseract OCR.

## Features

* **POST API** to extract Aadhaar details from a PDF link
* Robust image preprocessing for better OCR
* Auto-cleanup of temporary files
* Returns JSON output, ready for integration

---

## Requirements

* Python 3.7+

* [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system

  * **Windows:** [Download here](https://github.com/tesseract-ocr/tesseract/wiki/Downloads)
  * **Linux:** `sudo apt-get install tesseract-ocr`
  * **Mac:** `brew install tesseract`

* [Poppler](http://blog.alivate.com.au/poppler-windows/) (for PDF conversion)

  * **Linux:** `sudo apt-get install poppler-utils`
  * **Mac:** `brew install poppler`
  * **Windows:** [Download and add `bin` folder to PATH](http://blog.alivate.com.au/poppler-windows/)

* Python packages (install via pip):

```bash
pip install flask opencv-python-headless pytesseract numpy pdf2image requests certifi fuzzywuzzy
```

---

## Setup

1. **Clone this repo or copy the code files**
2. **Install the requirements** (see above)
3. **Set Tesseract path**
   (Optional if not in default location.
   The code defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe` for Windows.)

---

## Running the API

```bash
python ocrapp.py
```

The server will start at:
`http://localhost:5000`

---

## Usage

### **POST** `/extract-aadhaar`

**Request**

* Content-Type: `application/json`
* Body:

  ```json
  {
      "pdf_url": "https://example.com/path/to/aadhaar.pdf"
  }
  ```

**Response**

* On success:

  ```json
  {
      "Name": "Shubham Avinash Sawant",
      "Gender": "Male",
      "DOB/Year of Birth": "15-Jun-1998",
      "Aadhaar Number": "123412341234"
  }
  ```
* On error:

  ```json
  {
      "error": "Description of the error"
  }
  ```

---

## Notes

* The accuracy depends on PDF quality. Noisy, low-res, or scanned PDFs may produce less accurate results.
* The API deletes the downloaded PDF after processing.
* Currently supports **URL input only**. For file upload support, see TODOs.

---

