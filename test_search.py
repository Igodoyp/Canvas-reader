from vector_manager import VectorManager

db = VectorManager()

# 2. Write a fake strategy that sounds like one of your calculus problems
# Let's try something related to Double Integrals or Jacobians
fake_new_exercise = """
* Theorem: Green's Theorem.
* Strategy: Convert a line integral over a closed curve into a double integral over the bounded region.
* Computation: Calculate partial derivatives.
"""

print("Searching database for similar mathematical strategies...\n")

# 3. query
results = db.search_similar(query_strategy=fake_new_exercise, n_results=3)

print("Closest Match ID:", results['ids'][0][0])
print("Distance Score:", results['distances'][0][0]) 
print("Original File:", results['metadatas'][0][0]['source'])
print("Matched Strategy:\n", results['documents'][0][0])