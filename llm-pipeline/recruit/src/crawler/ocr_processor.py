import pandas as pd
import requests
from PIL import Image
from io import BytesIO
from surya.detection import DetectionPredictor
from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.common.surya.schema import TaskNames
import warnings
import pandas as pd

class OCRProcessor:
    def __init__(self):
        print("Loading Surya OCR models...")
        self.foundation_predictor = FoundationPredictor()
        self.det_predictor = DetectionPredictor()
        self.rec_predictor = RecognitionPredictor(self.foundation_predictor)
        print("Models loaded.")

    def process_csv(self, input_csv, output_csv, needs_ocr_col='Needs_OCR', image_urls_col='Image_URLs', context_col='Full_Context'):
        print(f"Reading {input_csv}...")
        try:
            df = pd.read_csv(input_csv)
        except FileNotFoundError:
            print(f"File {input_csv} not found.")
            return

        if needs_ocr_col not in df.columns or image_urls_col not in df.columns:
            print(f"Required columns ({needs_ocr_col}, {image_urls_col}) not found.")
            return

        if context_col not in df.columns:
            df[context_col] = ""

        # Filter rows needing OCR
        # Handle various boolean/string representations
        df[needs_ocr_col] = df[needs_ocr_col].astype(str).str.lower() == 'true'
        
        ocr_indices = df[df[needs_ocr_col]].index.tolist()
        print(f"Found {len(ocr_indices)} posts requiring OCR.")

        for idx in ocr_indices:
            row = df.loc[idx]
            image_urls = str(row[image_urls_col]).split(',')
            image_urls = [url.strip() for url in image_urls if url.strip()]

            if not image_urls:
                print(f"Row {idx}: Needs OCR but no images found.")
                continue

            print(f"Processing Row {idx}... {len(image_urls)} images.")
            
            extracted_texts = []
            
            for url in image_urls:
                try:
                    # Download image
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content)).convert("RGB")
                    
                    # Run OCR
                    print(f"  Running OCR on {url}...")
                    predictions = self.rec_predictor(
                        [image], 
                        [TaskNames.ocr_with_boxes], 
                        det_predictor=self.det_predictor
                    )
                    
                    if predictions and predictions[0].text_lines:
                        full_text = "\n".join([line.text for line in predictions[0].text_lines])
                        extracted_texts.append(full_text)
                    
                except Exception as e:
                    print(f"  Error processing image {url}: {e}")

            if extracted_texts:
                new_text = "\n\n[OCR Extracted Text]\n" + "\n\n".join(extracted_texts)
                # Append to context column
                current_context = str(df.loc[idx, context_col])
                if current_context == 'nan' or current_context == 'N/A' or not current_context:
                    df.loc[idx, context_col] = new_text
                else:
                    df.loc[idx, context_col] = current_context + "\n" + new_text
                
                # Mark as processed
                df.loc[idx, needs_ocr_col] = False
                print(f"  Updated {context_col} for row {idx}.")

        # Save result
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"Processing complete. Saved to {output_csv}")
    
 

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Input CSV file")
    parser.add_argument("--output", type=str, required=True, help="Output CSV file")
    args = parser.parse_args()

    processor = OCRProcessor()
    processor.process_csv(args.input, args.output)
