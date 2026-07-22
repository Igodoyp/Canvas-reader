import chromadb
import uuid

class VectorManager:
    def __init__(self):
        # This creates a local folder in your project to save the DB permanently
        self.client = chromadb.PersistentClient(path="./chroma_storage")
        
        # Think of a collection like a SQL table
        self.collection = self.client.get_or_create_collection(name="university_exercises")

    def save_exercise(self, strategy_text, course_id, visual_id, source_file):
        # 1. Generate a mathematically unique ID so we don't overwrite data
        unique_id = str(uuid.uuid4())
        
        # 2. Add the data to ChromaDB
        self.collection.add(
            documents=[strategy_text], # The text that gets vectorized for searching
            metadatas=[{"course_id": course_id, "visual_id": visual_id, "source": source_file}], # Filters
            ids=[unique_id]
        )
        print(f"Saved to ChromaDB: Exercise {visual_id}")

    def search_similar(self, query_strategy, n_results=2):
        # ChromaDB automatically embeds your query text and calculates the mathematical distance 
        # to all the vectors saved in your storage folder.
        results = self.collection.query(
            query_texts=[query_strategy],
            n_results=n_results
        )
        return results