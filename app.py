import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
import PyPDF2
import pandas as pd
from docx import Document
import tempfile
from dotenv import load_dotenv

# Set page config
st.set_page_config(
    page_title="Requirements Analysis & Test Case Generator",
    page_icon="🤖",
    layout="wide"
)

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = "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"
# Initialize session state
if 'processed_content' not in st.session_state:
    st.session_state.processed_content = None

def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def read_excel(file):
    df = pd.read_excel(file)
    return df.to_string()

def read_docx(file):
    doc = Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def process_document(file):
    file_extension = file.name.split('.')[-1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as tmp_file:
        tmp_file.write(file.getvalue())
        tmp_file_path = tmp_file.name
    
    try:
        if file_extension == 'pdf':
            content = read_pdf(tmp_file_path)
        elif file_extension in ['xlsx', 'xls']:
            content = read_excel(tmp_file_path)
        elif file_extension == 'docx':
            content = read_docx(tmp_file_path)
        else:
            st.error("Unsupported file format")
            return None
        
        return content
    finally:
        os.unlink(tmp_file_path)

# Create CrewAI agents
def create_agents():
    requirements_analyst = Agent(
        role='Requirements Analyst',
        goal='Analyze and understand software requirements thoroughly',
        backstory="""You are an expert requirements analyst with years of experience 
        in software development. You excel at breaking down complex requirements 
        into clear, actionable items.""",
        verbose=True
    )

    test_engineer = Agent(
        role='Test Engineer',
        goal='Generate comprehensive test cases with acceptance criteria',
        backstory="""You are a senior test engineer with extensive experience in 
        creating test cases and acceptance criteria. You ensure all requirements 
        are properly tested.""",
        verbose=True
    )
    
    # New Behavioral Agent
    behavioral_engineer = Agent(
        role='Behavioral Test Engineer',
        goal='Create decision-based test cases that model user behavior and system decision points',
        backstory="""You are a specialized test engineer focused on behavioral testing.
        You excel at identifying decision points in applications, modeling user behavior,
        and creating test cases that explore different decision paths and edge cases.
        Your expertise is in creating decision trees and scenario-based tests that reveal
        how systems handle complex user interactions and decision flows.""",
        verbose=True
    )

    return requirements_analyst, test_engineer, behavioral_engineer

def analyze_requirements(content):
    requirements_analyst, test_engineer, behavioral_engineer = create_agents()
    
    # Create tasks
    analysis_task = Task(
        description=f"""Analyze the following requirements and break them down into clear, 
        actionable items. Identify any ambiguities or potential issues:
        
        {content}""",
        expected_output="A list of detailed, actionable tasks based on the requirements.",
        agent=requirements_analyst
    )

    test_case_task = Task(
        description="""Based on the analyzed requirements, generate comprehensive test cases 
        with clear acceptance criteria for each requirement.""",
        expected_output="A list of test cases with acceptance criteria for each requirement.",
        agent=test_engineer
    )
    
    # New Behavioral Task
    behavioral_test_task = Task(
        description="""Based on the analyzed requirements, identify key decision points in the system
        and create decision-based test cases. Focus on:
        1. User decision flows and alternative paths
        2. System decision points and branching logic
        3. Edge cases and boundary conditions for decisions
        4. State transitions based on different decision outcomes
        5. Decision tables for complex conditional logic
        
        For each decision point, create test cases that explore different paths and outcomes.""",
        expected_output="""A detailed set of decision-based test cases with:
        - Decision points identified
        - Decision trees or tables where appropriate
        - Test scenarios covering different paths
        - Expected outcomes for each decision path
        - Edge cases and exception handling tests""",
        agent=behavioral_engineer
    )

    # Create and run the crew
    crew = Crew(
        agents=[requirements_analyst, test_engineer, behavioral_engineer],
        tasks=[analysis_task, test_case_task, behavioral_test_task],
        process=Process.sequential
    )

    result = crew.kickoff()
    return result

# Main UI
st.title("🤖 Requirements Analysis & Test Case Generator")

st.write("""
This application helps you analyze software requirements and generate test cases with acceptance criteria.
Upload your requirements document in PDF, Excel, or Word format to get started.
""")

uploaded_file = st.file_uploader(
    "Upload your requirements document",
    type=['pdf', 'xlsx', 'xls', 'docx']
)

if uploaded_file is not None:
    with st.spinner("Processing document..."):
        content = process_document(uploaded_file)
        if content:
            st.session_state.processed_content = content
            st.success("Document processed successfully!")

if st.session_state.processed_content:
    if st.button("Analyze Requirements and Generate Test Cases"):
        with st.spinner("Analyzing requirements and generating test cases..."):
            result = analyze_requirements(st.session_state.processed_content)
            
            # Convert to DataFrame and save
            final = pd.DataFrame(result)
            final.to_csv("output.csv")
            
            # Display results with tabs for different types of content
            st.subheader("Analysis Results")
            
            tabs = st.tabs(["Complete Analysis", "Behavioral Test Cases"])
            
            with tabs[0]:
                st.write(result)
            
            with tabs[1]:
                # Extract and display just the behavioral test cases
                if isinstance(result, dict) and "behavioral_test_task" in result:
                    st.write(result["behavioral_test_task"])
                else:
                    st.write("Behavioral test results are included in the complete analysis above")