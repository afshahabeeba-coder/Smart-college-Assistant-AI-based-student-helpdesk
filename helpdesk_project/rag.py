import os
import chromadb
from chromadb.utils import embedding_functions

class HelpdeskRAG:
    def __init__(self, db_path="./chroma_db", kb_path="knowledge_base/faq_guide.md"):
        self.db_path = db_path
        self.kb_path = kb_path
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Use default embedding function
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="helpdesk_faqs",
            embedding_function=self.embedding_fn
        )
        
        # Load documents if collection is empty
        if self.collection.count() == 0:
            self._load_knowledge_base()

    def _load_knowledge_base(self):
        if not os.path.exists(self.kb_path):
            print(f"Knowledge base path {self.kb_path} not found.")
            return

        with open(self.kb_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = content.split("## ")
        documents = []
        metadatas = []
        ids = []

        for i, section in enumerate(sections):
            if not section.strip():
                continue
            lines = section.strip().split("\n")
            title = lines[0]
            body = "\n".join(lines[1:]) if len(lines) > 1 else title
            
            documents.append(f"{title}\n{body}")
            metadatas.append({"source": title})
            ids.append(f"faq_{i}")

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"RAG loaded {len(documents)} documents successfully.")

    def ingest_documents(self, folder_path):
        # Compatibility wrapper expected by chatbot.py
        if os.path.exists(folder_path):
            kb_file = os.path.join(folder_path, "faq_guide.md")
            if os.path.exists(kb_file):
                self.kb_path = kb_file
                self._load_knowledge_base()

    def add_faq_entry(self, question, answer, tag="General"):
        try:
            doc = f"{question}\n{answer}"
            doc_id = f"custom_faq_{abs(hash(question))}"
            self.collection.upsert(
                documents=[doc],
                metadatas=[{"source": tag or "Custom FAQ"}],
                ids=[doc_id]
            )
            print(f"RAG dynamically indexed new FAQ: {question[:30]}...")
        except Exception as e:
            print(f"RAG add_faq_entry error: {e}")

    def query(self, query_text, n_results=2, max_distance=1.15):
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            if results and results.get('documents') and len(results['documents'][0]) > 0:
                distances = results.get('distances', [[]])[0]
                matched_docs = []
                for i, doc in enumerate(results['documents'][0]):
                    dist = distances[i] if i < len(distances) else 0
                    if dist <= max_distance:
                        matched_docs.append(doc)
                return matched_docs if matched_docs else None
        except Exception as e:
            print(f"RAG query error: {e}")
        return None

