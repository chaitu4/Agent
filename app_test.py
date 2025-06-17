import streamlit as st
import os
import PyPDF2
import pandas as pd
from docx import Document
import tempfile
import requests
import json

# Set page config
st.set_page_config(
    page_title="Requirements Analysis & Test Case Generator",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if 'processed_content' not in st.session_state:
    st.session_state.processed_content = None

def read_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def read_excel(file):
    """Extract text from Excel file"""
    try:
        df = pd.read_excel(file)
        return df.to_string()
    except Exception as e:
        st.error(f"Error reading Excel: {str(e)}")
        return None

def read_docx(file):
    """Extract text from Word document"""
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading Word document: {str(e)}")
        return None

def process_document(file):
    """Process uploaded document and extract text"""
    file_extension = file.name.split('.')[-1].lower()
    
    try:
        if file_extension == 'pdf':
            return read_pdf(file)
        elif file_extension in ['xlsx', 'xls']:
            return read_excel(file)
        elif file_extension == 'docx':
            return read_docx(file)
        else:
            st.error("Unsupported file format. Please upload PDF, Excel, or Word documents.")
            return None
    except Exception as e:
        st.error(f"Error processing document: {str(e)}")
        return None

def call_openai_api(prompt, max_tokens=1500):
    """Call OpenAI API with error handling"""
    try:
        # Get API key from Streamlit secrets
        if "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
        else:
            st.error("❌ OpenAI API key not found. Please add it to your Streamlit secrets.")
            return None
        
        # Make API call
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

def analyze_requirements(content):
    """Analyze requirements and generate comprehensive results"""
    
    # Requirements Analysis
    analysis_prompt = f"""
    As an expert Requirements Analyst, analyze the following requirements document and provide:

    1. **Functional Requirements**: List all functional requirements found
    2. **Non-Functional Requirements**: Identify performance, security, usability requirements
    3. **Ambiguities & Issues**: Point out unclear or problematic requirements
    4. **Recommendations**: Suggest improvements or clarifications needed

    Requirements Document:
    {content}

    Format your response clearly with headers and bullet points.
    """
    
    # Test Cases Generation
    test_cases_prompt = f"""
    As a Senior Test Engineer, create comprehensive test cases for the following requirements:

    {content}

    For each major requirement, provide:
    1. **Test Case ID & Name**
    2. **Objective**: What this test validates
    3. **Preconditions**: Setup required
    4. **Test Steps**: Detailed step-by-step actions
    5. **Expected Results**: What should happen
    6. **Acceptance Criteria**: Pass/fail conditions

    Include both positive and negative test scenarios.
    """
    
    # Behavioral Test Cases
    behavioral_prompt = f"""
    As a Behavioral Test Engineer, create decision-based test cases for:

    {content}

    Focus on:
    1. **User Decision Points**: Different paths users can take
    2. **System Decision Logic**: How the system responds to different inputs
    3. **Edge Cases**: Boundary conditions and error scenarios
    4. **State Transitions**: How the system changes state based on decisions
    5. **Decision Tables**: For complex conditional logic

    Create test scenarios that explore different decision paths and their outcomes.
    """
    
    results = {}
    
    # Get Requirements Analysis
    with st.spinner("🔍 Analyzing requirements..."):
        results['analysis'] = call_openai_api(analysis_prompt)
    
    # Get Test Cases
    with st.spinner("🧪 Generating test cases..."):
        results['test_cases'] = call_openai_api(test_cases_prompt)
    
    # Get Behavioral Tests
    with st.spinner("🎯 Creating behavioral test scenarios..."):
        results['behavioral_tests'] = call_openai_api(behavioral_prompt)
    
    return results

def save_results_to_csv(results):
    """Save results to CSV format"""
    try:
        data = []
        for key, value in results.items():
            if value:
                data.append({
                    'Analysis_Type': key.replace('_', ' ').title(),
                    'Content': value
                })
        
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
    except Exception as e:
        st.error(f"Error saving to CSV: {str(e)}")
        return None

# Main Application UI
def main():
    st.title("🤖 Requirements Analysis & Test Case Generator")
    
    st.markdown("""
    ### Welcome to the Requirements Analysis Tool!
    
    This application helps you:
    - 📋 **Analyze** software requirements documents
    - 🧪 **Generate** comprehensive test cases
    - 🎯 **Create** behavioral test scenarios
    - 📊 **Export** results for your team
    
    **Supported formats:** PDF, Excel (.xlsx, .xls), Word (.docx)
    """)
    
    # Check API key
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("""
        ⚠️ **API Key Required**
        
        Please add your OpenAI API key to Streamlit secrets:
        1. Go to your app dashboard
        2. Click 'Advanced settings'
        3. Add: `OPENAI_API_KEY = "your-key-here"`
        """)
        st.stop()
    
    # File Upload Section
    st.subheader("📁 Upload Your Requirements Document")
    
    uploaded_file = st.file_uploader(
        "Choose your requirements document",
        type=['pdf', 'xlsx', 'xls', 'docx'],
        help="Upload a PDF, Excel, or Word document containing your requirements"
    )
    
    if uploaded_file is not None:
        # File info
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size} bytes",
            "File type": uploaded_file.type
        }
        st.write("**File Details:**")
        st.json(file_details)
        
        # Process document
        with st.spinner("📖 Processing document..."):
            content = process_document(uploaded_file)
            
            if content:
                st.session_state.processed_content = content
                st.success("✅ Document processed successfully!")
                
                # Preview content
                with st.expander("📄 Preview Document Content"):
                    st.text_area(
                        "Extracted Text (first 1000 characters):",
                        content[:1000] + "..." if len(content) > 1000 else content,
                        height=200
                    )
            else:
                st.error("❌ Failed to process document. Please check the file format.")
    
    # Analysis Section
    if st.session_state.processed_content:
        st.subheader("🔬 Generate Analysis & Test Cases")
        
        if st.button("🚀 Start Analysis", type="primary"):
            with st.spinner("🤖 AI is working on your requirements..."):
                results = analyze_requirements(st.session_state.processed_content)
                
                if any(results.values()):
                    st.success("✅ Analysis completed!")
                    
                    # Display Results in Tabs
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📋 Requirements Analysis", 
                        "🧪 Test Cases", 
                        "🎯 Behavioral Tests",
                        "📊 Export Results"
                    ])
                    
                    with tab1:
                        st.subheader("Requirements Analysis")
                        if results.get('analysis'):
                            st.markdown(results['analysis'])
                        else:
                            st.error("Failed to generate requirements analysis")
                    
                    with tab2:
                        st.subheader("Test Cases")
                        if results.get('test_cases'):
                            st.markdown(results['test_cases'])
                        else:
                            st.error("Failed to generate test cases")
                    
                    with tab3:
                        st.subheader("Behavioral Test Scenarios")
                        if results.get('behavioral_tests'):
                            st.markdown(results['behavioral_tests'])
                        else:
                            st.error("Failed to generate behavioral tests")
                    
                    with tab4:
                        st.subheader("Export Results")
                        
                        # CSV Download
                        csv_data = save_results_to_csv(results)
                        if csv_data:
                            st.download_button(
                                label="📥 Download as CSV",
                                data=csv_data,
                                file_name="requirements_analysis.csv",
                                mime="text/csv"
                            )
                        
                        # Text Download
                        full_report = ""
                        for key, value in results.items():
                            if value:
                                full_report += f"\n\n{'='*50}\n"
                                full_report += f"{key.replace('_', ' ').upper()}\n"
                                full_report += f"{'='*50}\n\n"
                                full_report += value
                        
                        if full_report:
                            st.download_button(
                                label="📝 Download as Text",
                                data=full_report,
                                file_name="requirements_analysis.txt",
                                mime="text/plain"
                            )
                else:
                    st.error("❌ Failed to generate analysis. Please check your API key and try again.")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        Built with ❤️ using Streamlit | Powered by OpenAI GPT-3.5
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()