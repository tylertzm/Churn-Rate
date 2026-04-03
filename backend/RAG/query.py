import os
import chromadb
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import psycopg2

# ----------------------------
# Query routing
# ----------------------------
def route_query(query_text):
    if any(word in query_text.lower() for word in ["how many", "count", "average", "sum"]):
        return "sql"
    else:
        return "rag"

# ----------------------------
# Query Chroma
# ----------------------------
def query_chroma(collection, embed_model, query_text, top_k=20, rating_filter=None):
    query_embedding = embed_model.encode([query_text])[0]
    where_filter = {"rating": rating_filter} if rating_filter else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )
    return results['documents'][0], results['metadatas'][0]

# ----------------------------
# Generate answer with LLaMA
# ----------------------------
def generate_answer_llama(tokenizer, llama_model, context_sentences, question, max_tokens=300):
    context = "\n".join(context_sentences)
    prompt = f"Answer the question clearly and concisely in 3 sentences based on the context below.\n\nContext:\n{context}\n\nQuestion: {question}\n"

    inputs = tokenizer(prompt, return_tensors="pt").to(llama_model.device)
    with torch.no_grad():
        outputs = llama_model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated_tokens, skip_special_tokens=True)

# ----------------------------
# Main system
# ----------------------------
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

    # Initialize embedding model
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    # Initialize Chroma
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="churn_reviews")

    # Load LLaMA
    llama_model_id = "meta-llama/Llama-3.2-1B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(llama_model_id)
    llama_model = AutoModelForCausalLM.from_pretrained(
        llama_model_id,
        dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32,
        device_map="mps" if torch.backends.mps.is_available() else "cpu",
    )

    # Connect PostgreSQL
    PG_HOST = "localhost"
    PG_DB = "customer_reviews"
    PG_USER = "admin"
    PG_PASS = "7777"
    conn = psycopg2.connect(host=PG_HOST, dbname=PG_DB, user=PG_USER, password=PG_PASS)
    cursor = conn.cursor()

    # Example query
    user_query = "How many positive reviews are there and why are they positive?"
    route = route_query(user_query)

    num_positive = None
    if route == "sql":
        cursor.execute("SELECT COUNT(*) FROM trustpilot WHERE rating = 5;")
        num_positive = cursor.fetchone()[0]

    # Semantic retrieval for LLaMA context
    top_docs, _ = query_chroma(collection, embed_model, "Why are reviews positive?", top_k=50, rating_filter=5)
    answer = generate_answer_llama(tokenizer, llama_model, top_docs, "Why are reviews positive?")

    print(f"Number of positive reviews: {num_positive}")
    print("\nSummary of why reviews are positive:\n", answer)

    cursor.close()
    conn.close()