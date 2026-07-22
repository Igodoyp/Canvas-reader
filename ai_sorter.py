import os
from canvasapi import Canvas
from dotenv import load_dotenv
import google.genai as genai

class Sorter:
    def __init__(self):
        load_dotenv()
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.api_key = os.getenv('CANVAS_API_KEY')
        self.base_url = os.getenv('CANVAS_BASE_URL')
        self.canvas = Canvas(self.base_url, self.api_key)
        self.client = genai.Client(api_key=self.gemini_api_key)

    def classify_document(self, pdf_path, file_name):
        sample_file = self.client.files.upload(file=pdf_path)
        prompt = f"Analyze the provided document and its filename: '{file_name}'. Determine if this is a past exam/test ('exam'), a study guide/practice material ('guide'), or a non relevant document ('other'). Also, extract the academic year it was created. If the year is not explicitly stated, estimate it from the filename or context, or return 0. Output ONLY raw JSON, no markdown, in this exact format: {{'document_type': 'exam', 'year': 2023}}."
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[sample_file, prompt]
        )
        return response.text


#-----------------------TESTING THE SORTER-----------------------
if __name__ == "__main__":
    sorter = Sorter()
    pdf_path = "temp_guide.pdf"
    file_name = "Pauta examen Cálculo Multivariable 2025-2.pdf"
    classification_result = sorter.classify_document(pdf_path, file_name)
    cleaned_response = classification_result.replace("```json", "").replace("```", "").strip()
    print(cleaned_response)