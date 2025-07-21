import requests
import json
from typing import List, Dict, Optional
import re

# Add this function to clean up trailing commas in JSON

def clean_json_trailing_commas(json_str):
    # Remove trailing commas in arrays and objects
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    return json_str

# Add a function to strip prefixes from options

def strip_option_prefix(option):
    # Remove 'Option X:', 'A.', 'A)', 'A:', etc. from the start
    return re.sub(r'^(Option [A-D]:|[A-D][\.|\)|:])\s*', '', option).strip()

class LLMService:
    def __init__(self, model_name: str = "gemma3:4b", base_url: str = "http://localhost:11434"):
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
        """Generate quiz questions based on concept name only, using LLM knowledge, and force valid JSON output."""
        if not document_chunks:
            return []
        
        # Use the first chunk as the concept name (since we pass [f"Concept: {concept_name}"])
        concept_name = document_chunks[0].replace("Concept:", "").strip()
        
        system_prompt = f"""
You are an expert educator. Your job is to generate {num_questions} multiple choice quiz questions about the concept: \"{concept_name}\".

IMPORTANT INSTRUCTIONS:
- DO NOT ask for or expect any document content.
- Use your own knowledge of the concept.
- ALWAYS output ONLY valid JSON in the exact format below. Do NOT include any extra text, markdown, or explanations.
- The \"options\" array must be a list of 4 answer texts only (no prefixes, no letters, no numbers).
- The \"correct_answer\" field is the FULL TEXT of the correct option (must match exactly one of the options).
- The \"explanation\" field is a brief explanation of the correct answer.

EXAMPLE FORMAT (output ONLY this JSON, nothing else):

{{
  \"questions\": [
    {{
      \"question\": \"What is the capital of France?\",
      \"type\": \"multiple_choice\",
      \"options\": [\"Paris\", \"London\", \"Berlin\", \"Madrid\"],
      \"correct\": 0,
      \"correct_answer\": \"Paris\",
      \"explanation\": \"Paris is the capital of France.\"
    }}
  ]
}}
"""

        prompt = f"Concept: {concept_name}"

        response = self._make_request(prompt, system_prompt)
        print(f"LLM Response for quiz generation: {response[:500]}...")
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    # Clean up trailing commas before parsing
                    cleaned_json = clean_json_trailing_commas(json_match.group())
                    quiz_data = json.loads(cleaned_json)
                    questions = quiz_data.get("questions", [])
                    # Strip prefixes from all options
                    for q in questions:
                        if "options" in q:
                            q["options"] = [strip_option_prefix(opt) for opt in q["options"]]
                        # Also fix correct_answer if it was a letter
                        if "correct_answer" in q and q["correct_answer"] not in q["options"]:
                            abcd = ["A", "B", "C", "D"]
                            if q["correct_answer"].strip().upper() in abcd:
                                idx = abcd.index(q["correct_answer"].strip().upper())
                                if idx < len(q["options"]):
                                    q["correct_answer"] = q["options"][idx]
                                    q["correct"] = idx
                    # ... rest of the function as before ...
                    print(f"Generated {len(questions)} questions")
                    for i, q in enumerate(questions):
                        print(f"Question {i+1}: type={q.get('type')}, has_options={q.get('options') is not None}, options_count={len(q.get('options', []))}")
                        print(f"  Question text: {q.get('question', 'No question')}")
                        print(f"  Options: {q.get('options', 'No options')}")
                        print(f"  Correct: {q.get('correct', 'No correct')}")
                        print(f"  Correct answer: {q.get('correct_answer', 'No correct answer')}")
                        print("---")
                    return questions
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in extracted JSON: {e}")
                    print(f"Extracted JSON: {json_match.group()}")
                    return self._create_fallback_questions(document_chunks, num_questions, mastery_level)
            else:
                print("No JSON found in response, using fallback questions")
                return self._create_fallback_questions(document_chunks, num_questions, mastery_level)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return self._create_fallback_questions(document_chunks, num_questions, mastery_level)
    
    def _create_fallback_questions(self, chunks: List[str], num_questions: int, mastery_level: int = 1) -> List[Dict]:
        """Create simple fallback questions if LLM fails"""
        questions = []
        for i in range(min(num_questions, len(chunks))):
            chunk_text = chunks[i][:200] + "..." if len(chunks[i]) > 200 else chunks[i]
            
            if mastery_level == 1:
                # Recall level - multiple choice
                questions.append({
                    "question": f"What is the main topic discussed in this text?",
                    "type": "multiple_choice",
                    "options": [
                        "The main topic from the text",
                        "A related but different topic", 
                        "A completely unrelated topic",
                        "None of the above"
                    ],
                    "correct": 0,
                    "correct_answer": "The main topic from the text",
                    "explanation": "This tests basic recall of the main topic from the text."
                })
            elif mastery_level == 2:
                # Understanding level - multiple choice
                questions.append({
                    "question": f"What is the primary purpose of this text?",
                    "type": "multiple_choice",
                    "options": [
                        "To inform about the topic",
                        "To entertain the reader",
                        "To persuade the reader",
                        "To confuse the reader"
                    ],
                    "correct": 0,
                    "correct_answer": "To inform about the topic",
                    "explanation": "This tests comprehension of the text's purpose."
                })
            else:
                # Apply level - multiple choice scenario
                questions.append({
                    "question": f"Which of the following best demonstrates application of the concepts from this text?",
                    "type": "multiple_choice",
                    "options": [
                        "A practical example using the concepts",
                        "A summary of the concepts",
                        "A criticism of the concepts",
                        "A completely unrelated scenario"
                    ],
                    "correct": 0,
                    "correct_answer": "A practical example using the concepts",
                    "explanation": "This tests application and synthesis of knowledge."
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

    def test_quiz_generation(self, document_chunks: List[str], mastery_level: int = 1, num_questions: int = 1) -> List[Dict]:
        """Test function to debug quiz generation"""
        print("=== TESTING QUIZ GENERATION ===")
        print(f"Mastery level: {mastery_level}")
        print(f"Number of questions: {num_questions}")
        print(f"Document chunks: {len(document_chunks)}")
        
        questions = self.generate_quiz_questions(document_chunks, mastery_level, num_questions)
        
        print("=== FINAL QUESTIONS ===")
        for i, q in enumerate(questions):
            print(f"Question {i+1}:")
            print(f"  Type: {q.get('type')}")
            print(f"  Question: {q.get('question')}")
            print(f"  Options: {q.get('options')}")
            print(f"  Correct: {q.get('correct')}")
            print(f"  Correct Answer: {q.get('correct_answer')}")
            print("---")
        
        return questions 