import streamlit as st
import requests
import json
import PyPDF2
import pandas as pd
import io

# Gemini API key
api_key = "AIzaSyDRJt8UxRk4Xy5iYYplkeB8E8DhnyECmHY"

# Function to call Gemini API
def call_gemini_api(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 1,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 8192
        }
    }
    response = requests.post(
        url,
        headers=headers,
        params={"key": api_key},
        json=body
    )
    content = response.json()
    
    # Debugging: Print the full API response
    print("API Response:")
    print(content)
    
    # Extract the generated text
    if "candidates" in content and len(content["candidates"]) > 0:
        return content["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise Exception("No text generated by the API. Check the API response structure.")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Streamlit app
st.title("Restorative Dentistry MCQ Generating Agent")

# Upload PDF file
uploaded_file = st.file_uploader("Upload PDF File", type=["pdf"])

# Input fields
custom_prompt = st.text_area("Special Prompt to Inject", placeholder="Enter custom prompt here...")
cognition_level = st.selectbox("Level of Cognition", ["C1", "C2", "C3"])
difficulty_level = st.selectbox("Difficulty Level", ["Easy", "Moderate", "Hard"])

# Generate MCQ button
if st.button("Generate MCQ"):
    if uploaded_file is not None:
        try:
            # Extract text from PDF
            pdf_text = extract_text_from_pdf(uploaded_file)
            st.write("PDF Uploaded Successfully!")
            
            # Construct prompt for Gemini
            prompt = f'''
            Generate MCQs for Restorative Dentistry based on the following text:
            {pdf_text}

            Custom Prompt: {custom_prompt}
            Level of Cognition: {cognition_level}
            Difficulty Level: {difficulty_level}
            '''
            
            # Call Gemini API
            response = call_gemini_api(prompt)
            st.write("Generated MCQs:")
            st.write(response)
            
            # Parse MCQ data (example parsing logic)
            mcqs = response.split("\\n")
            mcqs = [q for q in mcqs if q.strip() and q.startswith(("Q", "1.", "2.", "3."))]  # Extract questions
            mcq_data = pd.DataFrame({
                "Question": mcqs,
                "Options": ["A) Option 1 | B) Option 2 | C) Option 3 | D) Option 4"] * len(mcqs),
                "Answer": ["A"] * len(mcqs)  # Placeholder for correct answer
            })
            
            # Display MCQ table
            st.write("MCQ Table:")
            st.table(mcq_data)
            
            # Download buttons
            st.write("Download MCQs:")
            csv = mcq_data.to_csv(index=False).encode("utf-8")
            st.download_button("Download as CSV", csv, "mcqs.csv", "text/csv")
            
            # Export to Word
            from docx import Document
            doc = Document()
            for index, row in mcq_data.iterrows():
                doc.add_paragraph(f"Question: {row['Question']}")
                doc.add_paragraph(f"Options: {row['Options']}")
                doc.add_paragraph(f"Answer: {row['Answer']}")
                doc.add_paragraph("\\n")
            doc_bytes = io.BytesIO()
            doc.save(doc_bytes)
            doc_bytes.seek(0)
            st.download_button("Download as Word", doc_bytes, "mcqs.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("Please upload a PDF file.")
