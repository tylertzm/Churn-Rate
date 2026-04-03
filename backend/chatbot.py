import os
import chromadb
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Dict
import uuid
import psycopg2

class ConversationSession:
    """Manages a single conversation session with history."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: List[Dict[str, str]] = []  # [{"role": "user/assistant", "content": "..."}]
        self.max_history = 5  # Keep last 5 exchanges (10 messages total)
    
    def add_message(self, role: str, content: str):
        """Add a message to history."""
        self.history.append({"role": role, "content": content})
        # Keep only last max_history exchanges (user + assistant pairs)
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]
    
    def get_history_context(self) -> str:
        """Format history for LLM context."""
        if not self.history:
            return ""
        
        formatted = "Previous conversation:\n"
        for msg in self.history[:-1]:  # Exclude the current question
            formatted += f"{msg['role'].capitalize()}: {msg['content']}\n"
        return formatted + "\n"
    
    def clear(self):
        """Clear conversation history."""
        self.history = []

class ChurnChatbot:
    def __init__(self):
        """Initialize the chatbot with RAG and LLM components."""
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.CHROMA_PATH = os.path.join(self.BASE_DIR, "RAG", "chroma_db")
        self.sessions: Dict[str, ConversationSession] = {}  # Store conversation sessions
        self.initialized = False
        self.error_message = None
        
        # PostgreSQL connection settings
        self.PG_HOST = "localhost"
        self.PG_DB = "customer_reviews"
        self.PG_USER = "admin"
        self.PG_PASS = "7777"
        
        try:
            # Initialize embedding model
            print("Loading embedding model...")
            self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Initialize ChromaDB
            print("Connecting to vector database...")
            self.client = chromadb.PersistentClient(path=self.CHROMA_PATH)
            self.collection = self.client.get_or_create_collection(name="churn_reviews")
            
            # Test PostgreSQL connection
            print("Testing PostgreSQL connection...")
            conn = psycopg2.connect(
                host=self.PG_HOST,
                dbname=self.PG_DB,
                user=self.PG_USER,
                password=self.PG_PASS
            )
            conn.close()
            print("PostgreSQL connection successful!")
            
            # Load LLaMA model
            print("Loading LLaMA model...")
            self.llama_model_id = "meta-llama/Llama-3.2-1B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(self.llama_model_id)
            self.llama_model = AutoModelForCausalLM.from_pretrained(
                self.llama_model_id,
                torch_dtype=torch.float16 if torch.backends.mps.is_available() else torch.float32,
                device_map="mps" if torch.backends.mps.is_available() else "cpu",
            )
            self.initialized = True
            print("Chatbot initialized successfully!")
        except Exception as e:
            self.initialized = False
            self.error_message = f"Failed to initialize chatbot: {str(e)}"
            print(f"ERROR: {self.error_message}")
            print("HINT: The vector database may be corrupted. Run 'python backend/RAG/ingestion.py' to rebuild it.")
    
    def get_or_create_session(self, session_id: str = None) -> ConversationSession:
        """Get existing session or create new one."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationSession(session_id)
        
        return self.sessions[session_id]
    
    def clear_session(self, session_id: str):
        """Clear a specific session's history."""
        if session_id in self.sessions:
            self.sessions[session_id].clear()
    
    def query_vector_db(self, query_text, top_k=20, rating_filter=None):
        """Query ChromaDB for relevant reviews and fetch complete data from PostgreSQL."""
        query_embedding = self.embed_model.encode([query_text])[0]
        where_filter = {"rating": rating_filter} if rating_filter else None
        
        # Get relevant documents from ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )
        
        # Extract unique row_ids from results
        row_ids = list(set([meta.get('row_id') for meta in results['metadatas'][0]]))[:10]
        
        if not row_ids:
            return [], []
        
        # Fetch complete reviews from PostgreSQL
        try:
            conn = psycopg2.connect(
                host=self.PG_HOST,
                dbname=self.PG_DB,
                user=self.PG_USER,
                password=self.PG_PASS
            )
            cursor = conn.cursor()
            
            # Convert row_ids to 1-based IDs for PostgreSQL (idx+1)
            pg_ids = [str(rid + 1) for rid in row_ids]
            placeholders = ','.join(['%s'] * len(pg_ids))
            
            query = f"""
                SELECT name, rating, title, body, date_raw, issue_list, churn_risk_level
                FROM trustpilot 
                WHERE id IN ({placeholders})
            """
            cursor.execute(query, pg_ids)
            rows = cursor.fetchall()
            
            # Format reviews for LLM
            formatted_reviews = []
            for row in rows:
                name, rating, title, body, date_raw, issue_list, risk = row
                review_parts = []
                review_parts.append(f"Customer: {name or 'Anonymous'}")
                review_parts.append(f"Rating: {rating}/5")
                if date_raw:
                    review_parts.append(f"Date: {date_raw}")
                if title:
                    review_parts.append(f"Title: {title}")
                if body:
                    review_parts.append(f"Review: {body}")
                if issue_list and issue_list != '[]':
                    review_parts.append(f"Issues: {issue_list}")
                if risk:
                    review_parts.append(f"Risk Level: {risk}")
                
                formatted_reviews.append(" | ".join(review_parts))
            
            cursor.close()
            conn.close()
            
            return formatted_reviews, results['metadatas'][0]
            
        except Exception as e:
            print(f"Error fetching from PostgreSQL: {e}")
            # Fallback to ChromaDB-only results
            reviews_dict = {}
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                row_id = meta.get('row_id')
                if row_id not in reviews_dict:
                    reviews_dict[row_id] = {
                        'rating': meta.get('rating'),
                        'parts': []
                    }
                reviews_dict[row_id]['parts'].append(doc)
            
            formatted_reviews = []
            for row_id, review_data in list(reviews_dict.items())[:10]:
                review_text = " | ".join(review_data['parts'])
                formatted_reviews.append(f"Review (rating: {review_data['rating']}): {review_text}")
            
            return formatted_reviews, results['metadatas'][0]
    
    def generate_response(self, context_sentences, question, conversation_history="", max_tokens=300):
        """Generate an answer using LLaMA based on retrieved context and conversation history."""
        context = "\n".join(context_sentences[:15])  # Limit context to avoid token overflow
        
        prompt = f"""You are a helpful customer churn analysis assistant. Answer the question using ONLY the information from the customer reviews provided below. Do not make up information.

{conversation_history}Customer reviews data:
{context}

Question: {question}

Instructions: Base your answer ONLY on the reviews above. Quote specific reviews when possible. If the reviews don't contain relevant information, say "I don't have enough information in the reviews to answer that."

Answer:"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024).to(self.llama_model.device)
        
        with torch.no_grad():
            outputs = self.llama_model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    
    def chat(self, user_message, session_id=None):
        """Main chat function that handles user queries with conversation history."""
        # Check if chatbot initialized successfully
        if not self.initialized:
            return {
                "status": "error",
                "answer": f"Chatbot is not available. {self.error_message or 'Unknown initialization error.'}",
                "sources_count": 0
            }
        
        try:
            # Get or create session
            session = self.get_or_create_session(session_id)
            
            # Add user message to history
            session.add_message("user", user_message)
            
            # Retrieve relevant documents from vector database
            documents, metadata = self.query_vector_db(user_message, top_k=15)
            
            # Get conversation history context
            history_context = session.get_history_context()
            
            # Generate response using LLM with conversation context
            response = self.generate_response(documents, user_message, history_context)
            
            # Add assistant response to history
            session.add_message("assistant", response)
            
            return {
                "status": "success",
                "answer": response,
                "sources_count": len(documents),
                "session_id": session.session_id,
                "history_length": len(session.history)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "answer": f"I encountered an error processing your question: {str(e)}",
                "sources_count": 0
            }

# Singleton instance for reuse
_chatbot_instance = None

def get_chatbot():
    """Get or create the chatbot singleton instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ChurnChatbot()
    return _chatbot_instance

# Test function
if __name__ == "__main__":
    chatbot = get_chatbot()
    
    # Test queries
    test_questions = [
        "What are the main reasons customers are churning?",
        "What do customers like about the service?",
        "Are there any issues with customer support?"
    ]
    
    for question in test_questions:
        print(f"\nQ: {question}")
        result = chatbot.chat(question)
        print(f"A: {result['answer']}")
        print(f"(Based on {result['sources_count']} reviews)")
