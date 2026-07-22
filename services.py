import os
import json
import tempfile

from importlib_metadata import files
from canvas_provider import CanvasProvider
from ai_analyst import Analyst
from ai_librarian import Librarian
from ai_sorter import Sorter
from vector_manager import VectorManager

# Inicialización de servicios
provider = CanvasProvider()
sorter = Sorter()
librarian = Librarian()
analyst = Analyst()
vector_manager = VectorManager()


# =====================================================================
# 1. FUNCIÓN AUTÓNOMA: POBLAR LA BASE DE DATOS CON EXÁMENES
# =====================================================================
def ingest_course_exams(course_id: int, selected_folder_ids: list, max_files: int = 1):
    """
    Busca los exámenes antiguos en Canvas, extrae las soluciones 
    y las guarda permanentemente en la Vector DB.
    """

    print("\n--- PHASE 1: INGESTING EXAMS & BUILDING DATABASE ---")
    files = list(provider.get_recent_files(course_id=course_id))

    exams_processed = 0
    
    for file in files:
        if exams_processed >= max_files:
            break
            
        if file.folder_id not in selected_folder_ids:
            continue

        print(file.display_name, file.created_at, file.url)
            
        # Descarga temporal segura usando tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.download(tmp.name)
            temp_path = tmp.name

        try:
            # 1. Clasificar documento
            sorter_response = sorter.classify_document(temp_path, file.display_name)
            doc_metadata = json.loads(sorter_response.replace("```json\n", "").replace("```", "").strip())

            doc_type = doc_metadata.get('document_type')
            year = doc_metadata.get('year', 0)
            print(f"Document type: {doc_type}, Year: {year}")
            
            # 2. Solo procesar si es EXAMEN reciente (>= 2023)
            if doc_type == 'exam' and year >= 2023:
                exercises_raw = librarian.extract_exercises(temp_path)
                clean_json = exercises_raw.replace("```json\n", "").replace("```", "").strip()
                exercise_list = json.loads(clean_json)

                for exercise in exercise_list:
                    # Resolver con IA
                    solution = analyst.solve_exercise(exercise['contenido'])
                    
                    # Guardar permanentemente en la base de datos vectorial
                    vector_manager.save_exercise(
                        strategy_text=solution, 
                        course_id=course_id, 
                        visual_id=exercise['id_visual'], 
                        source_file=file.display_name
                    )
                    print(f"Exercise ID: {exercise['id_visual']} processed and saved.")

                exams_processed += 1

        except json.JSONDecodeError:
            print(f"Error de formato JSON en {file.display_name}, saltando...")
        except Exception as e:
            print(f"Error procesando {file.display_name}: {e}")
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return {
        "status": "success",
        "course_id": course_id,
        "exams_ingested": exams_processed
    }


# =====================================================================
# 2. FUNCIÓN AUTÓNOMA: ANALIZAR Y RANKEAR GUÍAS CONTRA LA BD
# =====================================================================
def analyze_course_guides(course_id: int, selected_folder_ids: list, max_files: int = 1):
    """
    Busca las guías del curso en Canvas y las compara contra 
    la base de datos vectorial ya existente.
    """
    files = list(provider.get_recent_files(course_id=course_id))
    
    ranked_exercises = []
    guides_processed = 0

    for file in files:
        if guides_processed >= max_files:
            print(f"Límite de {max_files} guías alcanzado. Deteniendo análisis.")
            break

        if file.folder_id not in selected_folder_ids:
            continue

        print(f"Processing guide: {file.display_name}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.download(tmp.name)
            temp_path = tmp.name

        try:
            # 1. Clasificar documento
            sorter_response = sorter.classify_document(temp_path, file.display_name)
            doc_metadata = json.loads(sorter_response.replace("```json\n", "").replace("```", "").strip())
            
            # Solo procesamos si es GUÍA
            if doc_metadata.get('document_type') == 'guide':
                exercises_raw = librarian.extract_exercises(temp_path)
                clean_json = exercises_raw.replace("```json\n", "").replace("```", "").strip()
                exercise_list = json.loads(clean_json)

                for exercise in exercise_list:
                    # Resolver el ejercicio de la guía
                    solution = analyst.solve_exercise(exercise['contenido'])

                    # Buscar coincidencias en la BD vectorial PREVIAMENTE poblada
                    results = vector_manager.search_similar(query_strategy=solution, n_results=3)

                    if results and results.get('distances') and len(results['distances'][0]) > 0:
                        best_distance = results['distances'][0][0]
                        matched_exam = results['metadatas'][0][0]['source']

                        # Definir prioridad según la distancia vectorial
                        if best_distance < 0.5:
                            priority = "HIGH"
                        elif best_distance < 0.8:
                            priority = "MEDIUM"
                        else:
                            priority = "LOW"

                        ranked_exercises.append({
                            'guide_name': file.display_name,
                            'visual_id': exercise['id_visual'],
                            'distance': round(best_distance, 3),
                            'matched_exam': matched_exam,
                            'priority': priority
                        })
                

                        print(f"Exercise ID: {exercise['id_visual']}, Distance: {best_distance}, Matched Exam: {matched_exam}, Priority: {priority}")
                        
                guides_processed += 1

        except Exception as e:
            print(f"Error analizando guía {file.display_name}: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    print(f"\n Ranked exercises: {ranked_exercises}")

    # Ordenar por prioridad (menor distancia = más similar = mayor prioridad)
    ranked_exercises.sort(key=lambda x: x['distance'])

    return {
        "status": "success",
        "course_id": course_id,
        "total_ranked": len(ranked_exercises),
        "results": ranked_exercises
    }