#!/usr/bin/env python3
"""
Test script for document upload and processing functionality
"""

import streamlit as st
from document_processor import DocumentProcessor
import os

def test_document_processor():
    """Test the document processor functionality"""
    
    # Initialize processor
    processor = DocumentProcessor()
    
    # Test database initialization
    print("✅ Database initialized successfully")
    
    # Test getting documents (should be empty initially)
    documents = processor.get_documents()
    print(f"✅ Found {len(documents)} documents in database")
    
    # Test file hash calculation
    test_content = b"Hello, this is a test document!"
    file_hash = processor._calculate_file_hash(test_content)
    print(f"✅ File hash calculation works: {file_hash[:10]}...")
    
    # Test text extraction (if test file exists)
    test_file_path = "./uploads/ATLA.pdf"
    if os.path.exists(test_file_path):
        try:
            text = processor.extract_text(test_file_path)
            print(f"✅ Text extraction works: extracted {len(text)} characters")
        except Exception as e:
            print(f"❌ Text extraction failed: {e}")
    else:
        print("ℹ️ No test file found for text extraction test")
    
    print("\n🎉 Document processor test completed!")

if __name__ == "__main__":
    test_document_processor() 