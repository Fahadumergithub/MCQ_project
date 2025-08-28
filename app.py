# app.py
import streamlit as st
import requests
import json
import PyPDF2
import pandas as pd
import io
from docx import Document

# -------------------------
# Read secrets from Streamlit
# -------------------------
AZURE_OPENAI_KEY = st.secrets.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = st.secrets.get("AZURE_OPENAI_ENDPOINT", "https://mcqgpt.openai.azure.com/")
AZURE_OPENAI_DEPLOYMENT = st.secrets.get("AZURE_OPENAI_DEPLOYMENT", "o4-mini")
AZURE_OPENAI_API_VERSION = st.secrets.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Warn if API key missing.
if not AZURE_OPENAI_KEY:
    st.warning("Azure API key not found in Streamlit secrets. Add 'AZURE_OPENAI_API_KEY' before generating MCQs.")

# -------------------------
# Functions
# -------------------------
def call_azure_openai(prompt: str):
    """
    Call Azure OpenAI Chat Completions and return raw assistant text.
    Keeps output as plain text (same behavior as Gemini).
    """
    endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/") + f"/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }
    body = {
        "messages": [
            {"role": "system", "content": "You are an assistant that generates MCQs for dental education."},
            {"role": "user", "content": prompt}
        ],
        # keep temperature similar to previous (Gemini used 1)
        "temperature": 1.0,
        "top_p": 0.95,
        "max_completion_tokens":500,

    }

    resp = requests.post(endpoint, headers=headers, json=body, timeout=120)
    try:
        resp.raise_for_status()
    except Exception as e:
        # show response text to help debug
        raise RuntimeError(f"Azure request failed: {e}. Response text: {resp.text}")

    content = resp.json()

    # Debugging: print full API response in logs
    print("API Response:")
    print(json.dumps(content, indent=2))

    # Extract assistant message content (chat completion format)
    if "choices" in content and len(content["choices"]) > 0:
        # chat completions normally return choices[0].message.content
        return content["choices"][0].get("message", {}).get("content", "")
    else:
        # fallback: return raw json as string
        return json.dumps(content)

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text() or ""
        text += f"Page {page_num + 1}:\n{page_text}\n\n"
    return text, pdf_reader

# -------------------------
# Streamlit UI
# -------------------------
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
        if not AZURE_OPENAI_KEY:
            st.error("Missing Azure API key. Add 'AZURE_OPENAI_API_KEY' to Streamlit secrets.")
        else:
            try:
                # Extract text from PDF
                pdf_text, pdf_reader = extract_text_from_pdf(uploaded_file)
                st.write("PDF Uploaded Successfully!")

                # Construct prompt (kept identical to previous Gemini prompt)
                prompt = f'''
            Generate exactly 5 MCQs for Restorative Dentistry based on the following text:
            {pdf_text}

            Custom Prompt: {custom_prompt}
            Level of Cognition: {cognition_level}
            Difficulty Level: {difficulty_level}

            Ensure each question has 5 options (A, B, C, D, E) and a clear correct answer.
            Ensure all MCQ stems are based on dental clinical scenarios.
            '''

                # Call Azure OpenAI (returns plain text, same as Gemini)
                response_text = call_azure_openai(prompt)
                st.write("Generated MCQs:")
                st.write(response_text)

                # Parse MCQ data exactly as previous (line-splitting)
                mcqs = response_text.split("\n")
                mcqs = [q.strip() for q in mcqs if q.strip() and q.startswith(("Q", "1.", "2.", "3.", "4.", "5."))]  # Extract questions

                # Hardcoded options for demonstration (same as original)
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
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            st.write("Please refresh the page to start a new MCQ generation.")

# Footer
st.markdown(
    """
    <div style="text-align: center; margin-top: 20px;">
        <p>Powered by <a href="https://medentec.com/" target="_blank">Medentec</a></p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="text-align: center; margin-top: 10px;">
        <p>Code by <a href="https://www.linkedin.com/public-profile/settings?trk=d_flagship3_profile_self_view_public_profile" target="_blank">Dr. Fahad Umer</a></p>
    </div>
    """,
    unsafe_allow_html=True
)
