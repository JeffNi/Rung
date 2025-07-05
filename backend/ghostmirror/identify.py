import os
import pickle
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

EMBEDDING_DIR = os.path.join(os.path.dirname(__file__), "embeddings") 

def load_all_embeddings():
    memory = []
    if not os.path.exists(EMBEDDING_DIR):
        os.makedirs(EMBEDDING_DIR)
    for file in os.listdir(EMBEDDING_DIR):
        if file.endswith(".pkl"):
            with open(os.path.join(EMBEDDING_DIR, file), "rb") as f:
                data = pickle.load(f)
                memory.append(data)
    return memory

def save_new_speaker(label, embedding):
    filepath = os.path.join(EMBEDDING_DIR, f"{label}.pkl")
    with open(filepath, "wb") as f:
        pickle.dump({"label": label, "embedding": embedding}, f)

def match_speaker(new_embedding, memory, threshold=0.85):
    if not memory:
        return None
    embeddings = [entry["embedding"] for entry in memory]
    sims = cosine_similarity([new_embedding], embeddings)[0]
    max_idx = np.argmax(sims)
    if sims[max_idx] >= threshold:
        return memory[max_idx]["label"]
    return None

def generate_new_speaker_label(existing_labels):
    i = 0
    while True:
        label = f"Speaker_{chr(ord('A') + i)}"
        if label not in existing_labels:
            return label
        i += 1
