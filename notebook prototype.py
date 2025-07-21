import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_ace import st_ace
import json
from document_processor import DocumentProcessor
import time

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
        padding: 0.8rem;
        margin: 0.5rem 0;
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        background-color: white;
    }
    
    .concept-title {
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .concept-subtitle {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize document processor
if 'document_processor' not in st.session_state:
    st.session_state.document_processor = DocumentProcessor()

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
if 'documents' not in st.session_state:
    st.session_state.documents = []
if 'concepts' not in st.session_state:
    st.session_state.concepts = []
if 'upload_status' not in st.session_state:
    st.session_state.upload_status = []

# Sample concepts data
sample_concepts = [
    {
        "main": "Machine Learning Fundamentals",
        "sub": "Supervised Learning",
        "mastery_level": 1,
        "progress": 75
    },
    {
        "main": "Machine Learning Fundamentals", 
        "sub": "Unsupervised Learning",
        "mastery_level": 2,
        "progress": 45
    },
    {
        "main": "Deep Learning",
        "sub": "Neural Networks",
        "mastery_level": 1,
        "progress": 30
    },
    {
        "main": "Deep Learning",
        "sub": "Convolutional Networks",
        "mastery_level": 0,
        "progress": 0
    }
]

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
st.markdown('<h1 class="main-header">📚 NotebookLM Clone</h1>', unsafe_allow_html=True)

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
                col_info, col_actions = st.columns([3, 1])
                
                with col_info:
                    st.write(f"**Size:** {doc['file_size']:,} bytes")
                    st.write(f"**Chunks:** {doc['chunk_count']}")
                    st.write(f"**Status:** {doc['status']}")
                    st.write(f"**Uploaded:** {doc['upload_date']}")
                    if st.button("👁️", key=f"view_{doc['id']}", help="View chunks"):
                        chunks = st.session_state.document_processor.get_document_chunks(doc['id'])
                        st.write(f"**Document has {len(chunks)} chunks:**")
                        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                            st.text_area(f"Chunk {chunk['index']}", chunk['text'][:200] + "...", height=100)
                        if len(chunks) > 3:
                            st.info(f"... and {len(chunks) - 3} more chunks")
                
                with col_actions:
                    if st.button("🗑️", key=f"delete_{doc['id']}", help="Delete document"):
                        # TODO: Implement delete functionality
                        st.info("Delete functionality coming soon!")
                    

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
    
    # Quiz mode toggle and search
    col2a, col2b, col2c = st.columns([2, 1, 1])
    with col2a:
        user_input = st.text_input("Ask a question about your documents...", key="user_input")
    with col2b:
        if st.button("🔍 Search", type="secondary"):
            if user_input:
                search_results = st.session_state.document_processor.search_documents(user_input, top_k=5)
                if search_results:
                    st.session_state.chat_history.append({"role": "user", "content": f"Search: {user_input}"})
                    search_response = "**Search Results:**\n\n"
                    for i, result in enumerate(search_results, 1):
                        search_response += f"**{i}. From {result['document_name']} (similarity: {result['similarity']:.3f}):**\n"
                        search_response += f"{result['chunk_text'][:200]}...\n\n"
                    st.session_state.chat_history.append({"role": "assistant", "content": search_response})
                    st.rerun()
    with col2c:
        if st.button("🎯 Quiz Mode", type="primary"):
            st.session_state.quiz_mode = not st.session_state.quiz_mode
            if st.session_state.quiz_mode:
                st.session_state.current_quiz = sample_quiz
                st.session_state.current_question = 0
                st.session_state.quiz_answers = {}
                st.session_state.quiz_feedback = None
    
    # Chat history display
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant">{message["content"]}</div>', unsafe_allow_html=True)
        
        # Quiz mode display
        if st.session_state.quiz_mode and st.session_state.current_quiz:
            st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
            st.markdown(f"<h3>🎯 {st.session_state.current_quiz['title']}</h3>", unsafe_allow_html=True)
            
            current_q = st.session_state.current_quiz['questions'][st.session_state.current_question]
            
            # Display current question
            st.markdown(f'<div class="quiz-question">Question {st.session_state.current_question + 1}: {current_q["question"]}</div>', unsafe_allow_html=True)
            
            if current_q["type"] == "multiple_choice":
                # Multiple choice options
                selected_option = st.radio(
                    "Select your answer:",
                    current_q["options"],
                    key=f"quiz_option_{st.session_state.current_question}"
                )
                
                col_submit, col_next = st.columns([1, 1])
                with col_submit:
                    if st.button("Submit Answer", key="submit_quiz"):
                        is_correct = selected_option == current_q["options"][current_q["correct"]]
                        st.session_state.quiz_feedback = {
                            "correct": is_correct,
                            "message": "Correct!" if is_correct else f"Incorrect. The correct answer is: {current_q['options'][current_q['correct']]}"
                        }
                
                with col_next:
                    if st.session_state.quiz_feedback and st.button("Next Question", key="next_quiz"):
                        st.session_state.current_question += 1
                        st.session_state.quiz_feedback = None
                        if st.session_state.current_question >= len(st.session_state.current_quiz['questions']):
                            st.session_state.quiz_mode = False
                            st.session_state.current_quiz = None
                            st.rerun()
                
                # Display feedback
                if st.session_state.quiz_feedback:
                    feedback_class = "correct" if st.session_state.quiz_feedback["correct"] else "incorrect"
                    st.markdown(f'<div class="quiz-feedback {feedback_class}">{st.session_state.quiz_feedback["message"]}</div>', unsafe_allow_html=True)
            
            elif current_q["type"] == "text":
                # Text input for text questions
                text_answer = st.text_area("Your answer:", key=f"text_answer_{st.session_state.current_question}")
                
                col_submit, col_next = st.columns([1, 1])
                with col_submit:
                    if st.button("Submit Answer", key="submit_text"):
                        # Simple keyword matching for demo
                        keywords = ["classification", "regression", "discrete", "continuous"]
                        is_correct = any(keyword in text_answer.lower() for keyword in keywords)
                        st.session_state.quiz_feedback = {
                            "correct": is_correct,
                            "message": "Good answer!" if is_correct else f"Consider the difference between discrete and continuous outputs."
                        }
                
                with col_next:
                    if st.session_state.quiz_feedback and st.button("Next Question", key="next_text"):
                        st.session_state.current_question += 1
                        st.session_state.quiz_feedback = None
                        if st.session_state.current_question >= len(st.session_state.current_quiz['questions']):
                            st.session_state.quiz_mode = False
                            st.session_state.current_quiz = None
                            st.rerun()
                
                # Display feedback
                if st.session_state.quiz_feedback:
                    feedback_class = "correct" if st.session_state.quiz_feedback["correct"] else "incorrect"
                    st.markdown(f'<div class="quiz-feedback {feedback_class}">{st.session_state.quiz_feedback["message"]}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle user input
    if user_input and st.button("Send"):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Search documents for relevant content
        search_results = st.session_state.document_processor.search_documents(user_input, top_k=3)
        
        if search_results:
            # Create response based on search results
            context = "\n\n".join([f"From {result['document_name']}: {result['chunk_text'][:300]}..." for result in search_results])
            ai_response = f"Based on your uploaded documents, here's what I found:\n\n{context}\n\nThis is a simulated response. In a full implementation, this would be processed by an AI model."
        else:
            ai_response = f"I don't have any relevant information in your uploaded documents about '{user_input}'. Try uploading some documents first!"
        
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun()

# Right Column - Concepts and Mastery
with col3:
    st.markdown('<div class="column-header">🎯 Concepts & Mastery</div>', unsafe_allow_html=True)
    
    # Group concepts by main concept
    concept_groups = {}
    for concept in sample_concepts:
        main = concept["main"]
        if main not in concept_groups:
            concept_groups[main] = []
        concept_groups[main].append(concept)
    
    # Display concepts with mastery bars
    for main_concept, sub_concepts in concept_groups.items():
        st.markdown(f"<h4>{main_concept}</h4>", unsafe_allow_html=True)
        
        for concept in sub_concepts:
            st.markdown('<div class="concept-item">', unsafe_allow_html=True)
            st.markdown(f'<div class="concept-title">{concept["sub"]}</div>', unsafe_allow_html=True)
            
            # Mastery level indicator
            mastery_text = ""
            if concept["mastery_level"] == 0:
                mastery_text = "Not Started"
            elif concept["mastery_level"] == 1:
                mastery_text = "Recall Level"
            elif concept["mastery_level"] == 2:
                mastery_text = "Understanding Level"
            elif concept["mastery_level"] == 3:
                mastery_text = "Apply Level"
            
            st.markdown(f'<div class="concept-subtitle">Mastery: {mastery_text}</div>', unsafe_allow_html=True)
            
            # Mastery bar
            st.markdown('<div class="mastery-bar">', unsafe_allow_html=True)
            
            # Level 1 (Blue) - Always show if any progress
            if concept["mastery_level"] >= 1:
                level1_width = min(100, concept["progress"])
                st.markdown(f'<div class="mastery-level-1" style="width: {level1_width}%"></div>', unsafe_allow_html=True)
            
            # Level 2 (Gold) - Show if level 2 or higher
            if concept["mastery_level"] >= 2:
                level2_width = min(100, max(0, concept["progress"] - 100))
                if level2_width > 0:
                    st.markdown(f'<div class="mastery-level-2" style="width: {level2_width}%; position: absolute; top: 0; left: 0;"></div>', unsafe_allow_html=True)
            
            # Level 3 (Orange) - Show if level 3
            if concept["mastery_level"] >= 3:
                level3_width = min(100, max(0, concept["progress"] - 200))
                if level3_width > 0:
                    st.markdown(f'<div class="mastery-level-3" style="width: {level3_width}%; position: absolute; top: 0; left: 0;"></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Mastery level legend
    st.markdown("---")
    st.markdown("**Mastery Levels:**")
    st.markdown("🔵 **Blue**: Recall Level")
    st.markdown("🟡 **Gold**: Understanding Level") 
    st.markdown("🟠 **Orange**: Apply Level")

# Footer
st.markdown("---")
st.markdown("*This is a prototype of a NotebookLM clone. Features like document processing, AI responses, and concept extraction will be implemented in future versions.*")
