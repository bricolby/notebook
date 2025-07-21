import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_ace import st_ace
import json
from document_processor import DocumentProcessor
from llm_service import LLMService
import time

def _update_concept_mastery(concept_name: str, quiz_answers: dict):
    """Update concept mastery based on quiz performance"""
    # Get current concepts
    stored_concepts = st.session_state.document_processor.get_concepts()
    
    # Find the concept and update its mastery
    for concept in stored_concepts:
        if concept["main"] == concept_name:
            # Calculate performance
            total_questions = len(quiz_answers)
            correct_answers = sum(1 for answer in quiz_answers.values() if answer is True)
            
            print(f"Quiz performance: {correct_answers}/{total_questions} correct")
            
            # Update mastery based on performance
            if correct_answers == total_questions:  # All correct
                if concept["mastery_level"] < 3:  # Max level is 3
                    concept["mastery_level"] += 1
                    concept["progress"] = 0  # Reset progress for new level
                    print(f"Leveled up {concept_name} to level {concept['mastery_level']}")
                else:
                    concept["progress"] = min(300, concept["progress"] + 50)  # Cap at 300
                    print(f"Updated progress for {concept_name} to {concept['progress']}")
            elif correct_answers >= total_questions * 0.7:  # 70% or better
                concept["progress"] = min(300, concept["progress"] + 25)
                print(f"Good performance for {concept_name}, progress: {concept['progress']}")
            else:
                # Poor performance - slight progress or none
                concept["progress"] = max(0, concept["progress"] - 10)
                print(f"Poor performance for {concept_name}, progress: {concept['progress']}")
            
            # Update in database
            st.session_state.document_processor.update_concept_mastery(
                concept["id"], 
                concept["mastery_level"], 
                concept["progress"]
            )
            break

# Page configuration
st.set_page_config(
    page_title="NotebookLM Clone",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .column-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
    }
    
    .mastery-bar {
        background-color: #e0e0e0;
        border-radius: 0.5rem;
        height: 20px;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .mastery-level-1 {
        background-color: #1f77b4;
        height: 100%;
        border-radius: 0.5rem;
        transition: width 0.3s ease;
    }
    
    .mastery-level-2 {
        background-color: #ffd700;
        height: 100%;
        border-radius: 0.5rem;
        transition: width 0.3s ease;
    }
    
    .mastery-level-3 {
        background-color: #ff8c00;
        height: 100%;
        border-radius: 0.5rem;
        transition: width 0.3s ease;
    }
    
    .quiz-container {
        border: 2px solid #1f77b4;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #f8f9fa;
    }
    
    .quiz-question {
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background-color: white;
        border-radius: 0.3rem;
        border-left: 4px solid #1f77b4;
    }
    
    .quiz-option {
        padding: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #ddd;
        border-radius: 0.3rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .quiz-option:hover {
        background-color: #e3f2fd;
    }
    
    .quiz-option.selected {
        background-color: #bbdefb;
        border-color: #1f77b4;
    }
    
    .quiz-feedback {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    
    .quiz-feedback.correct {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .quiz-feedback.incorrect {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .chat-message {
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        max-width: 80%;
    }
    
    .chat-message.user {
        background-color: #e3f2fd;
        margin-left: auto;
        text-align: right;
    }
    
    .chat-message.assistant {
        background-color: #f5f5f5;
        margin-right: auto;
    }
    
    .concept-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        border: 1px solid #ddd;
        border-radius: 0.3rem;
        background-color: white;
        font-size: 0.8rem;
    }
    
    .concept-title {
        font-weight: bold;
        margin-bottom: 0.3rem;
        font-size: 0.9rem;
    }
    
    .concept-subtitle {
        font-size: 0.8rem;
        color: #666;
        margin-bottom: 0.3rem;
    }
    
    .main-concept {
        font-size: 1rem;
        font-weight: bold;
        color: #1f77b4;
        margin: 0.5rem 0 0.3rem 0;
        padding: 0.3rem;
        background-color: #f0f2f6;
        border-radius: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize services
if 'document_processor' not in st.session_state:
    st.session_state.document_processor = DocumentProcessor()

if 'llm_service' not in st.session_state:
    st.session_state.llm_service = LLMService()

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'quiz_mode' not in st.session_state:
    st.session_state.quiz_mode = False
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = None
if 'quiz_answers' not in st.session_state:
    st.session_state.quiz_answers = {}
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'quiz_feedback' not in st.session_state:
    st.session_state.quiz_feedback = None
if 'selected_concept' not in st.session_state:
    st.session_state.selected_concept = None
if 'concept_mastery_progress' not in st.session_state:
    st.session_state.concept_mastery_progress = {}  # {concept_id: {"correct_in_row": 0, "current_level": 0}}
if 'documents' not in st.session_state:
    st.session_state.documents = []
if 'concepts' not in st.session_state:
    st.session_state.concepts = []
if 'upload_status' not in st.session_state:
    st.session_state.upload_status = []
if 'ollama_status' not in st.session_state:
    st.session_state.ollama_status = None

# Check Ollama connection on startup
if st.session_state.ollama_status is None:
    st.session_state.ollama_status = st.session_state.llm_service.check_ollama_connection()



# Sample quiz data
sample_quiz = {
    "title": "Machine Learning Fundamentals Quiz",
    "questions": [
        {
            "question": "What is supervised learning?",
            "type": "multiple_choice",
            "options": [
                "Learning without labeled data",
                "Learning with labeled data",
                "Learning through trial and error",
                "Learning from environment feedback"
            ],
            "correct": 1
        },
        {
            "question": "Explain the difference between classification and regression.",
            "type": "text",
            "correct_answer": "Classification predicts discrete categories while regression predicts continuous values."
        },
        {
            "question": "Which algorithm is commonly used for classification?",
            "type": "multiple_choice",
            "options": [
                "Linear Regression",
                "Logistic Regression", 
                "K-means Clustering",
                "Principal Component Analysis"
            ],
            "correct": 1
        }
    ]
}

# Main app layout

# Create three columns
col1, col2, col3 = st.columns([1, 2, 1])

# Left Column - Document Upload and Management
with col1:
    st.markdown('<div class="column-header">📁 Documents</div>', unsafe_allow_html=True)
    
    # Upload section at the top
    st.markdown("### 📤 Upload Documents")
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=['pdf', 'txt', 'docx', 'md'],
        accept_multiple_files=True,
        help="Upload documents to study"
    )
    
    # Process uploaded files
    if uploaded_files:
        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                result = st.session_state.document_processor.process_document(uploaded_file, uploaded_file.name)
                
                if result["success"]:
                    if result["status"] == "already_exists":
                        st.success(f"✅ {result['message']}")
                    else:
                        st.success(f"✅ {result['message']}")
                        st.session_state.upload_status.append({
                            "filename": uploaded_file.name,
                            "status": "success",
                            "message": result["message"],
                            "chunk_count": result.get("chunk_count", 0)
                        })
                        
                        # Check Ollama connection before concept extraction
                        if st.session_state.ollama_status is None:
                            st.session_state.ollama_status = st.session_state.llm_service.check_ollama_connection()
                        
                        # Extract concepts at upload time if Ollama is available
                        if st.session_state.ollama_status and "chunks" in result:
                            with st.spinner("🔄 Extracting concepts from new document..."):
                                st.write(f"Debug: Processing {len(result['chunks'])} chunks for document {result['document_id']}")
                                new_concepts = st.session_state.document_processor.extract_and_store_concepts(
                                    result["chunks"], 
                                    st.session_state.llm_service,
                                    result["document_id"]
                                )
                                if new_concepts:
                                    st.success(f"📚 Extracted {len(new_concepts)} new concepts")
                                    # st.write(f"Debug: Concepts extracted: {new_concepts}")
                                    # # Show concept structure
                                    # for concept in new_concepts:
                                    #     st.write(f"  Concept: '{concept['main']}'")
                                else:
                                    st.info("No new concepts extracted from this document")
                                    st.write("Debug: No concepts were extracted - this might indicate an issue with the LLM or extraction process")
                        elif not st.session_state.ollama_status:
                            st.warning("⚠️ Ollama not connected - concepts cannot be extracted")
                        elif "chunks" not in result:
                            st.warning("⚠️ No chunks available for concept extraction")
                else:
                    st.error(f"❌ {result['message']}")
                    st.session_state.upload_status.append({
                        "filename": uploaded_file.name,
                        "status": "error",
                        "message": result["message"]
                    })
    
    # Display uploaded documents as individual expanders
    st.markdown("### 📚 Your Documents")
    
    # Get documents from database
    documents = st.session_state.document_processor.get_documents()
    
    if documents:
        for doc in documents:
            with st.expander(f"📄 {doc['filename']}", expanded=False):
                st.write(f"**Size:** {doc['file_size']:,} bytes")
                st.write(f"**Chunks:** {doc['chunk_count']}")
                st.write(f"**Status:** {doc['status']}")
                st.write(f"**Uploaded:** {doc['upload_date']}")
                
                # View button
                if st.button("👁️", key=f"view_{doc['id']}", help="View chunks"):
                    chunks = st.session_state.document_processor.get_document_chunks(doc['id'])
                    st.write(f"**Document has {len(chunks)} chunks:**")
                    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                        st.text_area(f"Chunk {chunk['index']}", chunk['text'][:200] + "...", height=100)
                    if len(chunks) > 3:
                        st.info(f"... and {len(chunks) - 3} more chunks")
                
                # Delete button
                if st.button("🗑️", key=f"delete_{doc['id']}", help="Delete document"):
                    with st.spinner(f"Deleting {doc['filename']}..."):
                        result = st.session_state.document_processor.delete_document(doc['id'])
                        
                        if result["success"]:
                            st.success(f"✅ {result['message']}")
                            st.rerun()  # Refresh the page to update the document list
                        else:
                            st.error(f"❌ {result['message']}")

    else:
        st.info("No documents uploaded yet. Upload some documents to get started!")
    
    # Display upload status history
    if st.session_state.upload_status:
        st.markdown("### 📊 Upload History")
        for status in st.session_state.upload_status[-5:]:  # Show last 5
            if status["status"] == "success":
                st.success(f"✅ {status['filename']} - {status['message']}")
            else:
                st.error(f"❌ {status['filename']} - {status['message']}")

# Middle Column - Chat Interface
with col2:
    st.markdown('<div class="column-header">💬 Chat Interface</div>', unsafe_allow_html=True)
    
    # Main content container - switches between chat and quiz
    main_container = st.container()
    
    with main_container:
        # Create a scrollable area
        st.markdown("""
        <style>
        .chat-scroll-container {
            height: 60vh;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            background-color: #f8f9fa;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Toggle between chat and quiz modes
        if st.session_state.quiz_mode:
            # Quiz Mode - create a fixed-height container
            st.markdown("""
            <style>
            .quiz-fixed-container {
                height: 60vh;
                border: 1px solid #ddd;
                border-radius: 0.5rem;
                padding: 1rem;
                margin-bottom: 1rem;
                background-color: #f8f9fa;
                overflow-y: auto;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Back to Chat button at the top
            if st.button("← Back to Chat", type="secondary"):
                st.session_state.quiz_mode = False
                st.session_state.selected_concept = None
                st.session_state.current_quiz = None
                st.session_state.current_question = 0
                st.session_state.quiz_answers = {}
                st.session_state.quiz_feedback = None
                st.rerun()
            
            # Create the fixed container
            quiz_container = st.container()
            
            with quiz_container:
                # st.markdown('<div class="quiz-fixed-container">', unsafe_allow_html=True)
                
                # Step 1: Concept Selection
                if st.session_state.selected_concept is None:
                    st.markdown('<div>🎯 Quiz Setup</div>', unsafe_allow_html=True)
                    st.markdown('<div>Select a concept to quiz on:</div>', unsafe_allow_html=True)
                    
                    # Get available concepts
                    stored_concepts = st.session_state.document_processor.get_concepts()
                    if stored_concepts:
                        # Create unique concept list (main concepts)
                        unique_concepts = list(set([concept["main"] for concept in stored_concepts]))
                        unique_concepts.sort()
                        
                        selected_concept_name = st.selectbox(
                            "Choose a concept:",
                            options=unique_concepts,
                            key="concept_selector"
                        )
                        
                        if st.button("Start Quiz", type="primary"):
                            st.session_state.selected_concept = selected_concept_name
                            st.rerun()
                    else:
                        st.warning("No concepts available. Upload some documents first!")
                        if st.button("Cancel Quiz"):
                            st.session_state.quiz_mode = False
                            st.rerun()
                
                # Step 2: Quiz Questions
                elif st.session_state.current_quiz is None:
                    # Generate quiz questions for selected concept
                    st.markdown(f'<div>🎯 Quiz on: {st.session_state.selected_concept}</div>', unsafe_allow_html=True)
                    
                    # Get mastery level for this concept
                    stored_concepts = st.session_state.document_processor.get_concepts()
                    concept_mastery = 0
                    for concept in stored_concepts:
                        if concept["main"] == st.session_state.selected_concept:
                            concept_mastery = concept["mastery_level"]
                            break
                    
                    # Convert mastery level to Bloom's Taxonomy name
                    bloom_names = {1: "Recall", 2: "Understanding", 3: "Apply"}
                    current_bloom = bloom_names.get(concept_mastery, "Unknown")
                    next_bloom = bloom_names.get(concept_mastery + 1, "Unknown")
                    
                    st.markdown(f'<div>Current Level: {current_bloom} (Level {concept_mastery})</div>', unsafe_allow_html=True)
                    # st.markdown(f'<div class="quiz-question">Next Level: {next_bloom}</div>', unsafe_allow_html=True)
                    
                    # Test button for debugging
                    # # if st.button("Test Quiz Generation", type="secondary"):
                    #     # Get chunks related to this concept
                    #     documents = st.session_state.document_processor.get_documents()
                    #     all_chunks = []
                    #     for doc in documents:
                    #         chunks = st.session_state.document_processor.get_document_chunks(doc['id'])
                    #         all_chunks.extend([chunk['text'] for chunk in chunks])
                        
                    #     if all_chunks and st.session_state.ollama_status:
                    #         with st.spinner("Testing quiz generation..."):
                    #             test_questions = st.session_state.llm_service.test_quiz_generation(
                    #                 all_chunks, 
                    #                 mastery_level=concept_mastery + 1,  # Next level
                    #                 num_questions=1
                    #             )
                    #             st.write("Test questions generated:", test_questions)
                    #     else:
                    #         st.error("No documents available or Ollama not connected")
                    
                    if st.button("Generate Questions", type="primary"):
                        # Get chunks related to this concept
                        documents = st.session_state.document_processor.get_documents()
                        all_chunks = []
                        for doc in documents:
                            chunks = st.session_state.document_processor.get_document_chunks(doc['id'])
                            all_chunks.extend([chunk['text'] for chunk in chunks])
                        
                        if all_chunks and st.session_state.ollama_status:
                            with st.spinner("Generating quiz questions..."):
                                questions = st.session_state.llm_service.generate_quiz_questions(
                                    all_chunks, 
                                    mastery_level=concept_mastery + 1,  # Next level
                                    num_questions=3
                                )
                                if questions:
                                    st.session_state.current_quiz = {
                                        "title": f"Quiz on {st.session_state.selected_concept}",
                                        "questions": questions,
                                        "concept": st.session_state.selected_concept,
                                        "mastery_level": concept_mastery
                                    }
                                    st.session_state.current_question = 0
                                    st.session_state.quiz_answers = {}
                                    st.session_state.quiz_feedback = None
                                    st.rerun()
                                else:
                                    st.error("Failed to generate quiz questions")
                        else:
                            st.error("No documents available or Ollama not connected")
                
                # Step 3: Display Quiz Questions
                elif st.session_state.current_quiz:
                    st.markdown(f'<div class="quiz-question">{st.session_state.current_quiz["title"]}</div>', unsafe_allow_html=True)
                    
                    current_q = st.session_state.current_quiz["questions"][st.session_state.current_question]
                    
                    # Console output for current question
                    print(f"\n=== QUESTION {st.session_state.current_question + 1} ===")
                    print(f"Question: {current_q.get('question')}")
                    print(f"Type: {current_q.get('type')}")
                    print(f"Options: {current_q.get('options')}")
                    print(f"Correct Index: {current_q.get('correct')}")
                    print(f"Correct Answer: {current_q.get('correct_answer')}")
                    print(f"Explanation: {current_q.get('explanation')}")
                    print("=" * 50)
                    
                    st.markdown(f'<div class="quiz-question">Question {st.session_state.current_question + 1}: {current_q["question"]}</div>', unsafe_allow_html=True)
                    
                    # # Debug: Show question structure
                    # st.write(f"Debug - Question type: {current_q.get('type')}")
                    # st.write(f"Debug - Has options: {'options' in current_q}")
                    # st.write(f"Debug - Options: {current_q.get('options', 'None')}")
                    
                    if current_q["type"] in ["multiple_choice", "recall"]:
                        if "options" in current_q and len(current_q["options"]) > 0:
                            # # Debug: Show correct answer info
                            # st.write(f"Debug - Correct index: {current_q.get('correct')}")
                            # st.write(f"Debug - Correct answer text: {current_q.get('correct_answer')}")
                            # st.write(f"Debug - Options: {current_q.get('options')}")
                            
                            for i, option in enumerate(current_q["options"]):
                                if st.button(f"{chr(65+i)}. {option}", key=f"quiz_option_{i}"):
                                    st.session_state.quiz_answers[st.session_state.current_question] = i
                                    correct_index = current_q.get("correct", 0)
                                    is_correct = i == correct_index
                                    print(f"ANSWER SELECTED:")
                                    print(f"  Selected index: {i}")
                                    print(f"  Selected option: {option}")
                                    print(f"  Correct index: {correct_index}")
                                    print(f"  Correct option: {current_q['options'][correct_index] if correct_index < len(current_q['options']) else 'Invalid'}")
                                    print(f"  Is correct: {is_correct}")
                                    st.write(f"Debug - Selected index: {i}, Correct index: {correct_index}, Is correct: {is_correct}")
                                    st.session_state.quiz_feedback = is_correct
                                    st.rerun()
                        else:
                            st.error("Multiple choice question missing options!")
                            st.write("Question data:", current_q)
                    
                    # Display feedback
                    if st.session_state.quiz_feedback is not None:
                        if st.session_state.quiz_feedback:
                            st.markdown('<div class="quiz-feedback correct">✅ Correct!</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="quiz-feedback incorrect">❌ Incorrect!</div>', unsafe_allow_html=True)
                        
                        # Show Bloom's Taxonomy level
                        # bloom_level = current_q.get("bloom_level", "Unknown")
                        # st.markdown(f'<div class="quiz-feedback">Bloom\'s Level: {bloom_level}</div>', unsafe_allow_html=True)
                        
                        # Show explanation with fallback
                        explanation = current_q.get("explanation", "No explanation available.")
                        st.markdown(f'<div class="quiz-feedback">Explanation: {explanation}</div>', unsafe_allow_html=True)
                        
                        if st.button("Next Question"):
                            st.session_state.current_question += 1
                            st.session_state.quiz_feedback = None
                            if st.session_state.current_question >= len(st.session_state.current_quiz["questions"]):
                                # Quiz completed - update mastery
                                _update_concept_mastery(st.session_state.current_quiz["concept"], st.session_state.quiz_answers)
                                st.session_state.quiz_mode = False
                                st.session_state.current_quiz = None
                                st.session_state.selected_concept = None
                            st.rerun()
                
                # Fallback case
                else:
                    st.info("Quiz state not recognized. Please try again.")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        else:
            # Chat Mode
            # Chat history display in scrollable container
            chat_html = '<div class="chat-scroll-container">'
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    chat_html += f'<div class="chat-message user">{message["content"]}</div>'
                else:
                    chat_html += f'<div class="chat-message assistant">{message["content"]}</div>'
            
            chat_html += '</div>'
            st.markdown(chat_html, unsafe_allow_html=True)
    
    # Input area at bottom
    input_container = st.container()
    with input_container:
        # Only show input controls in chat mode
        if not st.session_state.quiz_mode:
            # Inline input controls
            col_input, col_send, col_quiz = st.columns([3, 1, 1])
            
            with col_input:
                user_input = st.text_input("", label_visibility="collapsed", key="user_input", placeholder="Type your message here...")
            
            with col_send:
                send_button = st.button("Send", type="primary")
                if send_button and user_input:
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    
                    # Check Ollama connection
                    if not st.session_state.ollama_status:
                        st.session_state.ollama_status = st.session_state.llm_service.check_ollama_connection()
                    
                    if st.session_state.ollama_status:
                        # Search documents for relevant content
                        search_results = st.session_state.document_processor.search_documents(user_input, top_k=3)
                        
                        if search_results:
                            # Generate RAG response using LLM
                            with st.spinner("Generating response..."):
                                ai_response = st.session_state.llm_service.generate_rag_response(user_input, search_results)
                        else:
                            ai_response = "I don't have any relevant information in your uploaded documents about your question. Try uploading some documents first!"
                    else:
                        ai_response = "⚠️ Ollama is not running. Please start Ollama with a model (e.g., `ollama run gemma3:1b`) to enable AI responses."
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    st.rerun()
            
            with col_quiz:
                quiz_button = st.button("🎯 Quiz", type="secondary")
                if quiz_button:
                    st.session_state.quiz_mode = True
                    st.session_state.selected_concept = None
                    st.session_state.current_quiz = None
                    st.session_state.current_question = 0
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_feedback = None

# Right Column - Concepts and Mastery
with col3:
    st.markdown('<div class="column-header">🎯 Concepts & Mastery</div>', unsafe_allow_html=True)
    
    # Get stored concepts from database
    stored_concepts = st.session_state.document_processor.get_concepts()
    st.write(f"Debug: Found {len(stored_concepts)} stored concepts in database")
    
    if stored_concepts:
        # Group concepts by main concept
        concept_groups = {}
        for concept in stored_concepts:
            main = concept["main"]
            if main not in concept_groups:
                concept_groups[main] = []
            concept_groups[main].append(concept)
        
        # Display concepts with mastery bars
        for main_concept, sub_concepts in concept_groups.items():
            st.markdown(f'<div class="main-concept">{main_concept}</div>', unsafe_allow_html=True)
            
            for concept in sub_concepts:
                # st.markdown('<div class="concept-item">', unsafe_allow_html=True)
                st.markdown(f'<div class="concept-title">{concept["sub"]}</div>', unsafe_allow_html=True)
                
                # Mastery level indicator
                mastery_level = concept["mastery_level"]
                progress = concept["progress"]
                
                mastery_text = ""
                if mastery_level == 0:
                    mastery_text = "Not Started"
                elif mastery_level == 1:
                    mastery_text = "Recall Level"
                elif mastery_level == 2:
                    mastery_text = "Understanding Level"
                elif mastery_level == 3:
                    mastery_text = "Apply Level"
                
                st.markdown(f'<div class="concept-subtitle">Mastery: {mastery_text}</div>', unsafe_allow_html=True)
                
                # Mastery bar
                st.markdown('<div class="mastery-bar">', unsafe_allow_html=True)
                
                # Level 1 (Blue) - Always show if any progress
                if mastery_level >= 1:
                    level1_width = min(100, progress)
                    st.markdown(f'<div class="mastery-level-1" style="width: {level1_width}%"></div>', unsafe_allow_html=True)
                
                # Level 2 (Gold) - Show if level 2 or higher
                if mastery_level >= 2:
                    level2_width = min(100, max(0, progress - 100))
                    if level2_width > 0:
                        st.markdown(f'<div class="mastery-level-2" style="width: {level2_width}%; position: absolute; top: 0; left: 0;"></div>', unsafe_allow_html=True)
                
                # Level 3 (Orange) - Show if level 3
                if mastery_level >= 3:
                    level3_width = min(100, max(0, progress - 200))
                    if level3_width > 0:
                        st.markdown(f'<div class="mastery-level-3" style="width: {level3_width}%; position: absolute; top: 0; left: 0;"></div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📚 No concepts available yet. Upload some documents to extract concepts and start learning!")
    
    # Mastery level legend
    st.markdown("---")
    st.markdown("**Mastery Levels:**")
    st.markdown("🔵 **Blue**: Recall Level")
    st.markdown("🟡 **Gold**: Understanding Level") 
    st.markdown("🟠 **Orange**: Apply Level")
    
    # Ollama status indicator
    if st.session_state.ollama_status:
        st.success("✅ Ollama Connected (Gemma3:1b)")
    else:
        st.error("❌ Ollama Not Connected")
        st.info("Run `ollama run gemma3:1b` to enable AI features")