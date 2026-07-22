import json
from tqdm import tqdm
from ai_analyst import Analyst
from canvas_provider import CanvasProvider
from ai_librarian import Librarian
from ai_sorter import Sorter
import os
from dotenv import load_dotenv
from canvasapi import Canvas
import time
from vector_manager import VectorManager


course_id = 67599 #calc multi, curso antiguo

#init classes
sorter = Sorter()
provider = CanvasProvider()
provider.test_connection()
courses =provider.get_active_courses()
vector_manager = VectorManager()
librarian = Librarian()
analyst = Analyst()

# for course in courses:
#     print(course.name, course.id)

#buscar el id de setup folder para filtrarlo
setup_id = provider.get_setup_id(course_id=course_id)
print(f"Setup folder ID: {setup_id}, Course ID: {course_id}")

#get files
files = list(provider.get_recent_files(course_id=course_id))
print(f"Total files fetched: {len(files)}")

#-----------------------STARTUP LOOP-----------------------
#PROCESSES ALL OF THE OLD TESTS TO BUILD THE DB
print("\n--- PHASE 1: INGESTING EXAMS & BUILDING DATABASE ---")

guides_queue = []
valid_counter = 0
for file in tqdm(files, desc="Processing Canvas Files"):
    if valid_counter >= 30:    #counter para limitar archivos
        break
    
    if file.folder_id != setup_id:  #filtrar junk
        print(file.display_name, file.created_at, file.url)

        file.download("temp_guide.pdf")

        #doc type detection
        sorter_response = sorter.classify_document("temp_guide.pdf", file.display_name)
        doc_metadata = json.loads(sorter_response.replace("```json\n", "").replace("```", ""))
        doc_type = doc_metadata.get('document_type')
        year = doc_metadata.get('year')
        print(f"Document type: {doc_type}, Year: {year}")

        if doc_type == 'exam':
            if year >= 2023: #filtrar examenes viejos
                print("Procesando examen")
                exercises = librarian.extract_exercises("temp_guide.pdf")
                print(exercises)
                clean_exercises = exercises.replace("```json\n", "").replace("```json", "").replace("```", "").strip()
                try:
                    exercise_list = json.loads(clean_exercises)
                except json.JSONDecodeError:
                    print(f"Skipping document due to bad AI formatting.")
                    continue # Skips to the next file without crashing

                for exercise in exercise_list:
                    print(f"Processing Exercise ID: {exercise['id_visual']}")

                    solution = analyst.solve_exercise(exercise['contenido'])
                    print(f"Exercise ID: {exercise['id_visual']}, Solution Strategy: {solution}")

                    vector_manager.save_exercise(strategy_text=solution, course_id=course_id, visual_id=exercise['id_visual'], source_file=file.display_name)

                valid_counter += 1

            else:
                print("Examen viejo, saltando")
            
        elif doc_type == 'guide':
            print("Guide detected, sending to queue")
            guides_queue.append(file)
            valid_counter += 1

        elif doc_type == 'other':
            print("irrelevant document, skipping")
        
        else:
            print("Unknown document type, skipping")


#-----------------------COMPARING LOOP-----------------------
#SEARCHES THE DB FOR SIMILAR STRATEGIES
print("\n--- PHASE 2: ANALYZING GUIDES AGAINST DATABASE ---")

ranked_exercises = []

for guide in guides_queue:
    print(f"Processing guide: {guide.display_name}")

    #getting exercises
    guide.download("temp_guide.pdf")
    exercises = librarian.extract_exercises("temp_guide.pdf")
    print(exercises)
    clean_exercises = exercises.replace("```json\n", "").replace("```json", "").replace("```", "").strip()
    try:
        exercise_list = json.loads(clean_exercises)
    except json.JSONDecodeError:
        print(f"Skipping document due to bad AI formatting.")
        continue # Skips to the next file without crashing

    for exercise in exercise_list:
        print(f"Processing Exercise ID: {exercise['id_visual']}")

        #solves exercise
        solution = analyst.solve_exercise(exercise['contenido'])
        print(f"Exercise ID: {exercise['id_visual']}, Solution Strategy: {solution}")

        #searches for similar strategies in the database
        Results = vector_manager.search_similar(query_strategy=solution, n_results=3)

        #extracts best match
        best_distance = Results['distances'][0][0]
        matched_exam = Results['metadatas'][0][0]['source']

        ranked_exercises.append({
            'guide_name': guide.display_name,
            'visual_id': exercise['id_visual'],
            'distance': best_distance,
            'matched_exam': matched_exam
        })


# -------------------PHASE 3: Sorting and Formatting -------------------

ranked_exercises.sort(key=lambda x: x['distance']) #function to get the distance (the lowest the better)

print("\n=================================================")
print("🎯 ACADEMIC STRATEGIST: STUDY PRIORITY RANKING 🎯")
print("=================================================\n")

for ex in ranked_exercises:
    if ex['distance'] < 0.5:
        priority = "🔥 HIGH PRIORITY "
    elif ex['distance'] < 0.8:
        priority = "⚠️ MEDIUM PRIORITY"
    else:
        priority = "🧊 LOW PRIORITY   "

    print(f"{priority} | Guide: {ex['guide_name']} | Ex {ex['visual_id']}")
    print(f"  -> Matches: {ex['matched_exam']} (Distance: {ex['distance']:.3f})\n")