import requests
import json
from typing import List, Dict, Optional
import re

class LLMService:
    def __init__(self, model_name: str = "gemma3:1b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        
    def _make_request(self, prompt: str, system_prompt: str = None) -> str:
        """Make a request to Ollama API"""
        try:
            url = f"{self.api_url}/generate"
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            print(f"Making request to Ollama: {url}")
            print(f"Model: {self.model_name}")
            print(f"Payload keys: {list(payload.keys())}")
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "").strip()
            print(f"Ollama response length: {len(response_text)}")
            return response_text
            
        except requests.exceptions.RequestException as e:
            print(f"Error making request to Ollama: {e}")
            return f"Error: Unable to connect to Ollama. Please make sure Ollama is running with model {self.model_name}."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return f"Error: {str(e)}"
    
    def generate_rag_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate a response using RAG with provided context"""
        if not context_chunks:
            return "I don't have enough information to answer your question. Please upload some documents first."
        
        # Prepare context
        context_text = "\n\n".join([
            f"From {chunk['document_name']}: {chunk['chunk_text']}"
            for chunk in context_chunks
        ])
        
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided document context. 
        Always base your answers on the context provided. If the context doesn't contain enough information to answer the question, 
        say so clearly. Be concise but thorough in your responses."""
        
        prompt = f"""Context from uploaded documents:

{context_text}

Question: {query}

Please provide a helpful answer based on the context above:"""

        return self._make_request(prompt, system_prompt)
    
    def generate_quiz_questions(self, document_chunks: List[str], mastery_level: int = 1, num_questions: int = 3) -> List[Dict]:
        """Generate quiz questions based on document content and mastery level"""
        if not document_chunks:
            return []
        
        # Combine chunks for context
        context_text = "\n\n".join(document_chunks[:10])  # Use first 10 chunks
        
        # Define question types based on mastery level
        level_descriptions = {
            1: "recall and basic understanding",
            2: "comprehension and analysis", 
            3: "application and synthesis"
        }
        
        system_prompt = f"""You are an expert educator creating quiz questions. Generate {num_questions} questions at the {level_descriptions.get(mastery_level, 'basic')} level.
        
        For each question, provide:
        1. A clear question
        2. Multiple choice options (A, B, C, D) for multiple choice questions
        3. The correct answer
        4. A detailed explanation of why the answer is correct
        5. Question type (multiple_choice or text)
        
        Format your response as JSON with this structure:
        {{
            "questions": [
                {{
                    "question": "Question text",
                    "type": "multiple_choice",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct": 0,
                    "explanation": "Detailed explanation of the correct answer"
                }}
            ]
        }}"""
        
        prompt = f"""Based on the following document content, generate {num_questions} quiz questions at the {level_descriptions.get(mastery_level, 'basic')} level:

{context_text}

Focus on key concepts and important details from the text. Make sure questions test {level_descriptions.get(mastery_level, 'basic')} understanding."""

        response = self._make_request(prompt, system_prompt)
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                quiz_data = json.loads(json_match.group())
                return quiz_data.get("questions", [])
            else:
                # Fallback: create simple questions
                return self._create_fallback_questions(document_chunks, num_questions)
        except json.JSONDecodeError:
            return self._create_fallback_questions(document_chunks, num_questions)
    
    def _create_fallback_questions(self, chunks: List[str], num_questions: int) -> List[Dict]:
        """Create simple fallback questions if LLM fails"""
        questions = []
        for i in range(min(num_questions, len(chunks))):
            chunk_text = chunks[i][:200] + "..." if len(chunks[i]) > 200 else chunks[i]
            questions.append({
                "question": f"What is the main topic discussed in this text?",
                "type": "text",
                "correct_answer": "This is a text-based question about the content.",
                "explanation": "The answer should relate to the main concepts discussed in the provided text."
            })
        return questions
    
    def extract_concepts(self, document_chunks: List[str]) -> List[Dict]:
        """Extract main concepts from document content"""
        if not document_chunks:
            print("No document chunks provided for concept extraction")
            return []
        
        print(f"Extracting concepts from {len(document_chunks)} chunks")
        
        # Combine chunks for analysis
        context_text = "\n\n".join(document_chunks[:15])  # Use first 15 chunks
        print(f"Combined context length: {len(context_text)} characters")
        
        system_prompt = """You are an expert at analyzing educational content and extracting key concepts. 
        Your task is to identify the main concepts from the provided text.
        
        IMPORTANT: You must respond with ONLY valid JSON in this exact format:
        {
            "concepts": [
                {
                    "main": "Concept Name",
                    "sub": "Concept Name", 
                    "description": "Brief description of the concept"
                }
            ]
        }
        
        Focus on identifying the key topics, themes, or subjects from the document.
        Each concept should represent a distinct topic or theme.
        
        Do not include any other text, explanations, or formatting. Only return the JSON."""
        
        prompt = f"""Here is the document content to analyze:

{context_text}

Extract the key concepts from this content. Respond with ONLY the JSON format as specified in the system prompt."""

        print("Sending concept extraction request to Ollama...")
        response = self._make_request(prompt, system_prompt)
        print(f"Received response: {response[:200]}...")
        
        try:
            # First try to parse the entire response as JSON
            try:
                concept_data = json.loads(response.strip())
                concepts = concept_data.get("concepts", [])
                if concepts:
                    print(f"Successfully extracted {len(concepts)} concepts from direct JSON")
                    return concepts
            except json.JSONDecodeError:
                pass
            
            # If that fails, try to extract JSON from within the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    concept_data = json.loads(json_match.group())
                    concepts = concept_data.get("concepts", [])
                    if concepts:
                        print(f"Successfully extracted {len(concepts)} concepts from JSON match")
                        return concepts
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in match: {e}")
            
            print(f"No valid JSON found in response: {response[:200]}...")
            print("Using fallback concepts")
            # Fallback: create basic concepts
            return self._create_fallback_concepts(document_chunks)
            
        except Exception as e:
            print(f"Unexpected error in concept extraction: {e}")
            return self._create_fallback_concepts(document_chunks)
    
    def _create_fallback_concepts(self, chunks: List[str]) -> List[Dict]:
        """Create basic fallback concepts if LLM fails"""
        concepts = []
        if chunks:
            # Create concepts from the first few chunks
            for i, chunk in enumerate(chunks[:8]):  # Use first 8 chunks
                # Extract first few words as concept name
                words = chunk.split()[:6]
                concept_name = " ".join(words) if words else f"Topic {i+1}"
                
                concepts.append({
                    "main": concept_name[:50] + "..." if len(concept_name) > 50 else concept_name,
                    "sub": concept_name[:50] + "..." if len(concept_name) > 50 else concept_name,
                    "description": f"Key topic from document: {chunk[:100]}..."
                })
        return concepts
    
    def check_ollama_connection(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return [] 