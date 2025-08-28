import os
import requests
import pandas as pd
import streamlit as st

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = "https://mcqgpt.openai.azure.com"
DEPLOYMENT_NAME = "o4-mini"  # update if your deployment name is different
API_VERSION = "2024-12-01-preview"
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Streamlit app
st.title("Dental MCQ Generator")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file is not None:
    st.success("PDF Uploaded Successfully!")

    # Example user prompt (you can expand this)
    prompt = f"""
    Generate 5 MCQs from the content of the uploaded PDF.
    Return the result as a markdown table with these columns:
    Question | Options | Answer | Cognitive Level | Difficulty Level | Page Number | PDF Document Name
    """

    # Call Azure OpenAI
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
    }

    body = {
        "messages": [
            {"role": "system", "content": "You are an assistant that generates MCQs for dental education."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 1.0,
        "max_completion_tokens": 500
    }

    response = requests.post(
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}",
        headers=headers,
        json=body
    )

    if response.status_code == 200:
        result = response.json()
        mcq_output = result["choices"][0]["message"]["content"].strip()
        st.markdown("### MCQ Table:")
        st.markdown(mcq_output)
    else:
        st.error(f"Error: {response.text}")
