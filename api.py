from fastapi import FastAPI, HTTPException, BackgroundTasks
import os
import json
from pydantic import BaseModel
from typing import List

# Importas tus módulos locales
from canvas_provider import CanvasProvider
from ai_analyst import Analyst
from ai_librarian import Librarian
from ai_sorter import Sorter
from vector_manager import VectorManager
from services import ingest_course_exams, analyze_course_guides

app = FastAPI(
    title="Nexamate API",
    description="Backend oficial para conectar Canvas y procesar certámenes con IA"
)

# Inicialización de servicios
provider = CanvasProvider()
sorter = Sorter()
librarian = Librarian()
analyst = Analyst()
vector_manager = VectorManager()

# Modelo "Aduana" para validar los datos que envía Flutter
class IngestionRequest(BaseModel):
    selected_folder_ids: List[int]


# ------------------- RUTAS Y ENDPOINTS -------------------

@app.get("/zzz")
def home():
    return {"status": "ok", "message": "Servidor de Nexamate funcionando 🚀"}


# 1. Dashboard: Lista de cursos del estudiante
@app.get("/api/courses")
def get_courses():
    try:
        courses = provider.get_active_courses()
        summary_list = [provider.get_course_summary(c) for c in courses]
        return {"status": "success", "data": summary_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2. Pre-visualización: Recomendación de carpetas (Fricción Cero)
@app.get("/api/courses/{course_id}/folders-preview")
def get_folder_recommendations(course_id: int):
    try:
        folders = provider.get_course_folders(course_id)
        
        keywords_utiles = ['certamen', 'prueba', 'guia', 'ejercicio', 'pauta', 'examen']
        keywords_basura = ['_setup', 'syllabus', 'reglamento', 'calendario']
        
        lista_carpetas = []
        for folder in folders:
            nombre = folder.name.lower()
            if any(kb in nombre for kb in keywords_basura) or folder.files_count == 0:
                continue
                
            lista_carpetas.append({
                "folder_id": folder.id,
                "name": folder.name,
                "file_count": folder.files_count,
                "is_recommended": any(ku in nombre for ku in keywords_utiles)
            })
            
        return {"status": "success", "folders": lista_carpetas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3. Ingesta: Poblar la BD de exámenes antiguos (En segundo plano)
@app.post("/api/courses/{course_id}/ingest")
def start_course_ingestion(course_id: int, payload: IngestionRequest, background_tasks: BackgroundTasks):
    carpetas_elegidas = payload.selected_folder_ids
    if not carpetas_elegidas:
        return {"status": "error", "message": "Debes seleccionar al menos una carpeta"}

    # Ejecuta el trabajo pesado sin bloquear la pantalla del usuario
    background_tasks.add_task(
        ingest_course_exams, 
        course_id=course_id, 
        selected_folder_ids=carpetas_elegidas
    )
    
    return {
        "status": "processing",
        "message": "¡Entrenamiento iniciado! Te avisaremos cuando los ejercicios estén listos."
    }


# 4. Análisis: Comparar guías contra la BD y responder con el ranking
@app.post("/api/courses/{course_id}/analyze-guides")
def analyze_guides_endpoint(course_id: int, payload: IngestionRequest):
    carpetas_elegidas = payload.selected_folder_ids
    if not carpetas_elegidas:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos una carpeta")

    try:
        resultado = analyze_course_guides(
            course_id=course_id, 
            selected_folder_ids=carpetas_elegidas
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando guías: {str(e)}")