import os
import hashlib
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
import PyPDF2
from docx import Document
import markdown
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document as LangchainDocument

class DocumentProcessor:
    def __init__(self, upload_dir: str = "./uploads", db_path: str = "./documents.db"):
        self.upload_dir = Path(upload_dir)
        self.db_path = db_path
        self.upload_dir.mkdir(exist_ok=True)
        
        # Initialize the embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for document metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                vector_path TEXT,
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'uploaded'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                chunk_index INTEGER,
                chunk_text TEXT,
                embedding_path TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error extracting text from PDF {file_path}: {e}")
        return text
    
    def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error extracting text from DOCX {file_path}: {e}")
        return text
    
    def _extract_text_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error extracting text from TXT {file_path}: {e}")
            return ""
    
    def _extract_text_from_md(self, file_path: Path) -> str:
        """Extract text from Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
                # Convert markdown to plain text
                html = markdown.markdown(md_content)
                # Simple HTML to text conversion (you might want to use BeautifulSoup for better results)
                return html.replace('<', ' <').replace('>', '> ')
        except Exception as e:
            print(f"Error extracting text from MD {file_path}: {e}")
            return ""
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from various file formats"""
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            return self._extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            return self._extract_text_from_docx(file_path)
        elif file_extension == '.txt':
            return self._extract_text_from_txt(file_path)
        elif file_extension == '.md':
            return self._extract_text_from_md(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def save_file(self, uploaded_file, filename: str) -> Path:
        """Save uploaded file to uploads directory"""
        file_path = self.upload_dir / filename
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return file_path
    
    def process_document(self, uploaded_file, filename: str) -> Dict:
        """Main method to process uploaded document"""
        try:
            # Calculate file hash
            file_content = uploaded_file.getbuffer()
            file_hash = self._calculate_file_hash(file_content)
            
            # Check if file already exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
            existing_doc = cursor.fetchone()
            
            if existing_doc:
                conn.close()
                return {
                    "success": True,
                    "message": f"Document '{filename}' already exists in database",
                    "document_id": existing_doc[0],
                    "status": "already_exists"
                }
            
            # Save file
            file_path = self.save_file(uploaded_file, filename)
            file_size = len(file_content)
            
            # Extract text
            text = self.extract_text(file_path)
            if not text.strip():
                return {
                    "success": False,
                    "message": f"Could not extract text from '{filename}'"
                }
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Generate embeddings for chunks
            embeddings = self.embedding_model.encode(chunks)
            
            # Save embeddings and chunks
            vector_path = file_path.with_suffix('.pkl')
            chunk_data = {
                'chunks': chunks,
                'embeddings': embeddings
            }
            
            with open(vector_path, 'wb') as f:
                pickle.dump(chunk_data, f)
            
            # Save to database
            cursor.execute('''
                INSERT INTO documents (filename, file_hash, file_path, file_size, vector_path, chunk_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (filename, file_hash, str(file_path), file_size, str(vector_path), len(chunks), 'processed'))
            
            document_id = cursor.lastrowid
            
            # Save chunk metadata
            for i, chunk in enumerate(chunks):
                cursor.execute('''
                    INSERT INTO chunks (document_id, chunk_index, chunk_text)
                    VALUES (?, ?, ?)
                ''', (document_id, i, chunk))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"Successfully processed '{filename}' ({len(chunks)} chunks)",
                "document_id": document_id,
                "chunk_count": len(chunks),
                "status": "processed"
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                "success": False,
                "message": f"Error processing '{filename}': {str(e)}",
                "details": error_details
            }
    
    def get_documents(self) -> List[Dict]:
        """Get all documents from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_size, upload_date, chunk_count, status
            FROM documents
            ORDER BY upload_date DESC
        ''')
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                'id': row[0],
                'filename': row[1],
                'file_size': row[2],
                'upload_date': row[3],
                'chunk_count': row[4],
                'status': row[5]
            })
        
        conn.close()
        return documents
    
    def get_document_chunks(self, document_id: int) -> List[Dict]:
        """Get chunks for a specific document"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chunk_index, chunk_text
            FROM chunks
            WHERE document_id = ?
            ORDER BY chunk_index
        ''', (document_id,))
        
        chunks = []
        for row in cursor.fetchall():
            chunks.append({
                'index': row[0],
                'text': row[1]
            })
        
        conn.close()
        return chunks
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search documents using vector similarity"""
        # Encode query
        query_embedding = self.embedding_model.encode([query])
        
        results = []
        
        # Get all documents
        documents = self.get_documents()
        
        for doc in documents:
            # Load embeddings for this document
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT vector_path FROM documents WHERE id = ?", (doc['id'],))
            vector_path = cursor.fetchone()[0]
            
            if vector_path and os.path.exists(vector_path):
                with open(vector_path, 'rb') as f:
                    chunk_data = pickle.load(f)
                
                # Calculate similarities
                similarities = np.dot(chunk_data['embeddings'], query_embedding.T).flatten()
                
                # Get top chunks for this document
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                
                for idx in top_indices:
                    if similarities[idx] > 0.3:  # Similarity threshold
                        results.append({
                            'document_id': doc['id'],
                            'document_name': doc['filename'],
                            'chunk_index': int(idx),
                            'chunk_text': chunk_data['chunks'][idx],
                            'similarity': float(similarities[idx])
                        })
            
            conn.close()
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k * len(documents)] 