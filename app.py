import streamlit as st
import requests
import PyPDF2
import io
import pandas as pd

# Azure OpenAI settings
AZURE_ENDPOINT = "https://mcqgpt.openai.azure.com"
DEPLOYMENT_NAME = "o4-mini"  # your deployment name
API_VERSION = "2024-12-01-preview"
API_KEY = "YOUR_AZURE_OPENAI_API_KEY"

# Function to call Azure OpenAI
def generate_mcqs(prompt):
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"
    headers = {"Content-Type": "application/json", "api-key": API_KEY}

    body = {
        "messages": [
            {"role": "system", "content": "You are an assistant that generates MCQs for dental education."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 1.0,
        "max_completion_tokens": 500
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    else:
        st.error(f"Azure request failed: {response.status_code} - {response.text}")
        return None

# Function to extract text from PDF
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Streamlit UI
st.title("MCQ Generator for Dental Education")

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_file is not None:
    pdf_text = extract_text_from_pdf(uploaded_file)
    st.success("PDF Uploaded Successfully!")

    if st.button("Generate MCQs"):
        prompt = f"Generate 5 MCQs with the following columns: Question, Options, Answer, Cognitive Level, Difficulty Level, Page Number, PDF Document Name. Use the content below:\n\n{pdf_text[:4000]}"

        mcq_output = generate_mcqs(prompt)

        if mcq_output:
            st.subheader("Generated MCQs")
            st.write(mcq_output)

            # Try to parse into a table if possible
            try:
                rows = [row.strip() for row in mcq_output.split("\n") if row.strip()]
                df = pd.DataFrame(rows, columns=["MCQs"])
                st.dataframe(df)
            except Exception:
                st.text(mcq_output)
