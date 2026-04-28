import io
import logging
import os
import shutil

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        logger.info("OCR Processor initialized")
        self.configure_tesseract()

    def configure_tesseract(self):
        """Configure Tesseract executable path for Windows environments."""
        discovered_path = shutil.which("tesseract")
        fallback_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        tesseract_path = discovered_path or (fallback_path if os.path.exists(fallback_path) else None)
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info("Using Tesseract executable at %s", tesseract_path)
        else:
            logger.warning("Tesseract executable was not found. OCR requests will fail until it is installed.")

    def extract_text_from_image(self, image_data: bytes) -> str:
        """
        Extract text from prescription image using OCR
        """
        try:
            # Convert bytes to image
            image = Image.open(io.BytesIO(image_data))
            
            # Preprocess image for better OCR
            img_cv = self.preprocess_image(image)
            
            # Use Tesseract OCR to extract text
            text = pytesseract.image_to_string(img_cv, config="--psm 6")
            
            logger.info(f"OCR extracted text: {text}")
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            raise Exception(f"Text extraction from image failed: {str(e)}")

    def preprocess_image(self, image):
        """Preprocess image to improve OCR accuracy"""
        # Convert to OpenCV format
        img_cv = np.array(image)
        
        # Convert to grayscale
        if len(img_cv.shape) == 3:
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
        
        # Apply thresholding
        img_cv = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Remove noise
        img_cv = cv2.medianBlur(img_cv, 3)
        
        return img_cv

# Global instance
ocr_processor = OCRProcessor()
