import os
from canvasapi import Canvas
from dotenv import load_dotenv
import google.genai as genai


class Librarian:
    def __init__(self):
        load_dotenv()
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.api_key = os.getenv('CANVAS_API_KEY')
        self.base_url = os.getenv('CANVAS_BASE_URL')
        self.canvas = Canvas(self.base_url, self.api_key)
        self.client = genai.Client(api_key=self.gemini_api_key)

    def extract_exercises(self, pdf_path):
        sample_file = self.client.files.upload(file=pdf_path)
        prompt = f"You are an academic assistant. Analyze this document. Extract each exercise or question. Return ONLY a JSON array where each object has 'id_visual' (the exercise number/letter) and 'contenido' (the full text of the question). Do not include markdown code blocks, just the raw JSON."
        
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[sample_file, prompt]
        )
        return response.text
    

#----------------------MOSTRAR MODELOS DISPONIBLES----------------------
# load_dotenv()
# client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
# for model in client.models.list():
#     print(model.name) 

# ---------------------- SIMPLE TEST ----------------------
if __name__ == "__main__":
    librarian = Librarian()
    # Replace 'sample.pdf' with a real PDF path for actual use
    pdf_path = "temp_guide.pdf"
    try:
        result = librarian.extract_exercises(pdf_path)
        print("Extracted exercises:", result)
    except Exception as e:
        print("Error during extraction:", e)