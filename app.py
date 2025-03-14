import streamlit as st
import requests
import json
import PyPDF2
import pandas as pd
import io
from docx import Document

# Read API key from secrets.toml
api_key = st.secrets["GEMINI_API_KEY"]

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
    for page_num, page in enumerate(pdf_reader.pages):
        text += f"Page {page_num + 1}:\n{page.extract_text()}\n\n"
    return text, pdf_reader

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
            pdf_text, pdf_reader = extract_text_from_pdf(uploaded_file)
            st.write("PDF Uploaded Successfully!")
            
            # Construct prompt for Gemini
            prompt = f'''
            Generate exactly 5 MCQs for Restorative Dentistry based on the following text:
            {pdf_text}

            Custom Prompt: {custom_prompt}
            Level of Cognition: {cognition_level}
            Difficulty Level: {difficulty_level}

            Ensure each question has 5 options (A, B, C, D, E) and a clear correct answer.
            Ensure all MCQ stems are based on dental clinical scenarios.
            '''
            
            # Call Gemini API
            response = call_gemini_api(prompt)
            st.write("Generated MCQs:")
            st.write(response)
            
            # Parse MCQ data
            mcqs = response.split("\n")
            mcqs = [q.strip() for q in mcqs if q.strip() and q.startswith(("Q", "1.", "2.", "3.", "4.", "5."))]  # Extract questions
            
            # Hardcoded options for demonstration
            options = [
                "A) Composite resin | B) Amalgam | C) Glass ionomer | D) Zirconia | E) Porcelain",
                "A) Isolation | B) Anesthesia | C) Polishing | D) Etching | E) Bonding",
                "A) Caries | B) Fracture | C) Wear | D) Sensitivity | E) Discoloration",
                "A) Fluoride | B) Sugar | C) Acid | D) Bacteria | E) Trauma",
                "A) Micro-retentions | B) Whitening | C) Desensitization | D) Bonding | E) Polishing"
            ]
            
            answers = ["A", "B", "C", "D", "E"]  # Hardcoded correct answers (placeholder)
            
            # Create a DataFrame for the MCQs with additional attributes
            mcq_data = pd.DataFrame({
                "Question": mcqs[:5],  # Ensure only 5 questions
                "Options": options[:5],  # Ensure only 5 options per question
                "Answer": answers[:5],  # Ensure only 5 answers
                "Cognitive Level": [cognition_level] * 5,  # Add cognitive level
                "Difficulty Level": [difficulty_level] * 5,  # Add difficulty level
                "Page Number": ["Page 1"] * 5,  # Add page number (placeholder, can be updated)
                "PDF Document Name": [uploaded_file.name] * 5  # Add PDF document name
            })
            
            # Display MCQ table
            st.write("MCQ Table:")
            st.table(mcq_data)
            
            # Download as CSV
            csv = mcq_data.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="mcqs.csv",
                mime="text/csv"
            )
            
            # Download as Word
            doc = Document()
            doc.add_heading("Generated MCQs", level=1)
            for index, row in mcq_data.iterrows():
                doc.add_paragraph(f"Question: {row['Question']}")
                doc.add_paragraph(f"Options: {row['Options']}")
                doc.add_paragraph(f"Answer: {row['Answer']}")
                doc.add_paragraph(f"Cognitive Level: {row['Cognitive Level']}")
                doc.add_paragraph(f"Difficulty Level: {row['Difficulty Level']}")
                doc.add_paragraph(f"Page Number: {row['Page Number']}")
                doc.add_paragraph(f"PDF Document Name: {row['PDF Document Name']}")
                doc.add_paragraph("\n")
            doc_bytes = io.BytesIO()
            doc.save(doc_bytes)
            doc_bytes.seek(0)
            st.download_button(
                label="Download as Word",
                data=doc_bytes,
                file_name="mcqs.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("Please upload a PDF file.")

# Add "New MCQ" button to refresh the page
if st.button("New MCQ"):
    st.rerun()  # Use st.rerun() if available, otherwise use the session state workaround

# Add "Powered by Medentec" with hyperlink
st.markdown(
    """
    <div style="text-align: center; margin-top: 20px;">
        <p>Powered by <a href="https://medentec.com/" target="_blank">Medentec</a></p>
    </div>
    """,
    unsafe_allow_html=True
)

# Add "Code by Dr. Fahad Umer" with LinkedIn hyperlink
st.markdown(
    """
    <div style="text-align: center; margin-top: 10px;">
        <p>Code by <a href="https://www.linkedin.com/public-profile/settings?trk=d_flagship3_profile_self_view_public_profile" target="_blank">Dr. Fahad Umer</a></p>
    </div>
    """,
    unsafe_allow_html=True
)
