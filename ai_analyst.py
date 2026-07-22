import os
from canvasapi import Canvas
from dotenv import load_dotenv
import google.genai as genai

class Analyst:
    def __init__(self):
        load_dotenv()
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai.Client(api_key=self.gemini_api_key)
    
    def solve_exercise(self, exercise_text):
        prompt = f"You are an expert mathematical architect. Extract the core algorithmic strategy to solve this exercise. Output must be extremely concise, dense, and bulleted. Focus ONLY on the mathematical principles, theorem names, coordinate systems, and geometric setups. DO NOT use filler words, conversational text, or generic advice like 'visualize the region'. Maximum 75 words."
        
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, exercise_text]
        )
        return response.text
    
