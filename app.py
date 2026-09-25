import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from modules.chatbot import answer_question, explain_simply
from modules.database import (
    add_activity,
    get_dashboard_stats,
    get_recent_activity,
    init_db,
    increment_questions,
    record_quiz_score,
)
from modules.document_processor import process_uploaded_file
from modules.quiz_generator import generate_quiz
from modules.rag import clear_index, index_document, search_documents
from utils.helpers import load_json, save_uploaded_file

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
COURSES = load_json(DATA_DIR / "courses.json")
FAQS = load_json(DATA_DIR / "faq.json")

st.set_page_config(page_title="AI Student Academic Assistant", page_icon="🎓", layout="wide")
init_db()


def inject_styles():
    css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def course_names():
    return [course["name"] for course in COURSES]


def selected_course(name):
    return next((course for course in COURSES if course["name"] == name), COURSES[0])


def render_sidebar():
    with st.sidebar:
        st.markdown("<div class='brand'><span class='brand-mark'>🎓</span><div><strong>AI Academic</strong><small>Student Assistant</small></div></div>", unsafe_allow_html=True)
        st.divider()
        page = st.radio(
            "Navigate",
            ["Dashboard", "AI Chat", "Courses", "Study Materials", "Important Topics", "FAQ", "Explain Simply", "Quiz", "Search", "Settings"],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("RAG-powered learning workspace")
        st.caption("Your uploaded material stays local unless you choose an AI API.")
    return page


def render_header(title, subtitle):
    st.markdown(f"<div class='page-header'><div><p class='eyebrow'>STUDENT WORKSPACE</p><h1>{title}</h1><p>{subtitle}</p></div></div>", unsafe_allow_html=True)


def dashboard():
    render_header("Welcome to your academic workspace", "Ask questions, explore courses, upload material, and practice with focused quizzes.")
    stats = get_dashboard_stats()
    cols = st.columns(4)
    labels = [("Courses", len(COURSES), "Active curriculum"), ("Materials", stats["materials"], "Indexed documents"), ("Questions", stats["questions"], "This session and beyond"), ("Quiz average", f"{stats['quiz_score']}%", "Best recorded score")]
    for col, (label, value, hint) in zip(cols, labels):
        with col:
            st.markdown(f"<div class='stat-card'><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-heading'><div><p class='eyebrow'>QUICK START</p><h2>What would you like to do?</h2></div></div>", unsafe_allow_html=True)
    cards = [("💬", "Ask the assistant", "Get a clear answer grounded in your study materials.", "AI Chat"), ("📄", "Add study material", "Upload a PDF, TXT, or DOCX and build your private knowledge base.", "Study Materials"), ("🧠", "Test your knowledge", "Generate a short multiple-choice quiz for any course topic.", "Quiz")]
    card_cols = st.columns(3)
    for col, (icon, title, text, target) in zip(card_cols, cards):
        with col:
            st.markdown(f"<div class='feature-card'><div class='feature-icon'>{icon}</div><h3>{title}</h3><p>{text}</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-heading'><div><p class='eyebrow'>ACTIVITY</p><h2>Recent activity</h2></div></div>", unsafe_allow_html=True)
    activities = get_recent_activity()
    if activities:
        for item in activities:
            st.markdown(f"<div class='activity-row'><span>{item['kind']}</span><div><strong>{item['title']}</strong><small>{item['created_at']}</small></div></div>", unsafe_allow_html=True)
    else:
        st.info("Your activity will appear here as you study.")


def chat_page():
    render_header("AI Chat", "A calm place to ask course questions and reason through difficult concepts.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask a question about your coursework...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = answer_question(question, search_documents(question))
            st.markdown(result)
        increment_questions()
        add_activity("💬", f"Asked: {question[:60]}")


def courses_page():
    render_header("Courses", "Browse syllabus coverage and use each course as a focused starting point.")
    name = st.selectbox("Select a course", course_names())
    course = selected_course(name)
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown(f"<div class='course-panel'><p class='eyebrow'>COURSE OVERVIEW</p><h2>{course['name']}</h2><p>{course['description']}</p></div>", unsafe_allow_html=True)
        st.subheader("Syllabus")
        for index, unit in enumerate(course["syllabus"], 1):
            with st.expander(f"Unit {index}: {unit['title']}"):
                st.write(unit["summary"])
                st.write("Topics: " + ", ".join(unit["topics"]))
    with right:
        st.subheader("Ask about this course")
        question = st.text_area("Your question", placeholder=f"What should I know about {name}?", height=120)
        if st.button("Ask course assistant", type="primary"):
            if not question.strip():
                st.warning("Please enter a question first.")
            else:
                context = "\n".join(topic for topic in course["important_topics"])
                st.markdown(answer_question(f"Course: {name}. {question}", search_documents(question), extra_context=context))
                increment_questions()


def materials_page():
    render_header("Study Materials", "Upload your notes and turn them into a searchable, question-ready study companion.")
    uploaded = st.file_uploader("Upload PDF, TXT, or DOCX", type=["pdf", "txt", "docx"])
    if uploaded:
        if uploaded.size > 10 * 1024 * 1024:
            st.error("This file is larger than 10 MB. Please upload a smaller document.")
        elif st.button("Process and index material", type="primary"):
            with st.spinner("Extracting text and building your index..."):
                try:
                    path = save_uploaded_file(uploaded, UPLOAD_DIR)
                    text = process_uploaded_file(path)
                    if not text.strip():
                        st.error("The document did not contain readable text.")
                    else:
                        chunks = index_document(uploaded.name, text)
                        st.success(f"Indexed {chunks} chunks from {uploaded.name}.")
                        add_activity("📄", f"Indexed {uploaded.name}")
                except ValueError as error:
                    st.error(str(error))
                except Exception:
                    st.error("The document could not be processed. Check its format and try again.")
    st.divider()
    st.subheader("Ask your uploaded material")
    material_question = st.text_input("Question", placeholder="What does the uploaded material say about...?", key="material_question")
    if st.button("Search material"):
        if not material_question.strip():
            st.warning("Please enter a question first.")
        else:
            results = search_documents(material_question)
            if not results:
                st.info("No close match was found in uploaded material yet.")
            else:
                st.markdown(answer_question(material_question, results))
                increment_questions()


def topics_page():
    render_header("Important Topics", "A compact revision map for every course in the demo curriculum.")
    for course in COURSES:
        with st.expander(course["name"], expanded=course is COURSES[0]):
            st.write("  •  ".join(course["important_topics"]))


def faq_page():
    render_header("Frequently Asked Questions", "Quick answers for common academic concepts.")
    question = st.selectbox("Choose a question", [item["question"] for item in FAQS])
    answer = next(item["answer"] for item in FAQS if item["question"] == question)
    st.markdown(f"<div class='answer-box'><p class='eyebrow'>ANSWER</p><h2>{question}</h2><p>{answer}</p></div>", unsafe_allow_html=True)


def explain_page():
    render_header("Explain Simply", "Turn a difficult topic into a short explanation you can actually remember.")
    topic = st.text_input("Topic", placeholder="e.g. recursion, normalization, overfitting")
    if st.button("Explain simply", type="primary"):
        if not topic.strip():
            st.warning("Enter a topic to explain.")
        else:
            st.markdown(explain_simply(topic))


def quiz_page():
    render_header("Quiz Studio", "Generate a small practice set and use feedback to guide your next revision session.")
    name = st.selectbox("Course", course_names(), key="quiz_course")
    course = selected_course(name)
    topic = st.selectbox("Topic", course["important_topics"])
    count = st.slider("Number of questions", 1, 5, 3)
    if st.button("Generate quiz", type="primary"):
        st.session_state.quiz = generate_quiz(name, topic, count)
    quiz = st.session_state.get("quiz")
    if quiz:
        with st.form("quiz_form"):
            answers = []
            for index, item in enumerate(quiz):
                answers.append(st.radio(f"{index + 1}. {item['question']}", item["options"], key=f"quiz_{index}"))
            submitted = st.form_submit_button("Check answers")
        if submitted:
            score = sum(answer == item["answer"] for answer, item in zip(answers, quiz))
            record_quiz_score(round(score / len(quiz) * 100))
            st.success(f"You scored {score}/{len(quiz)} ({round(score / len(quiz) * 100)}%).")
            for item, answer in zip(quiz, answers):
                st.write(f"**{item['answer']}**: {item['explanation']}")


def search_page():
    render_header("Search", "Find a course, topic, FAQ, or indexed study material from one place.")
    query = st.text_input("Search everything", placeholder="Try: trees, normalization, operating system")
    if query.strip():
        lowered = query.lower()
        matches = []
        for course in COURSES:
            searchable = json.dumps(course).lower()
            if lowered in searchable:
                matches.append(("Course", course["name"], course["description"]))
        for item in FAQS:
            if lowered in json.dumps(item).lower():
                matches.append(("FAQ", item["question"], item["answer"]))
        for result in search_documents(query):
            matches.append(("Material", result["source"], result["text"][:240] + "..."))
        if matches:
            for kind, title, snippet in matches:
                st.markdown(f"<div class='search-result'><span>{kind}</span><h3>{title}</h3><p>{snippet}</p></div>", unsafe_allow_html=True)
        else:
            st.info("No results found. Try a broader term.")


def settings_page():
    render_header("Settings", "Check the local configuration used by your assistant.")
    configured = bool(os.getenv("OPENAI_API_KEY"))
    st.markdown(f"**AI API:** {'Configured' if configured else 'Not configured - local fallback is active'}")
    st.markdown("**Supported files:** PDF, TXT, DOCX (maximum 10 MB per upload)")
    if st.button("Clear indexed material"):
        clear_index()
        st.success("Indexed material cleared.")


inject_styles()
page = render_sidebar()
if page == "Dashboard":
    dashboard()
elif page == "AI Chat":
    chat_page()
elif page == "Courses":
    courses_page()
elif page == "Study Materials":
    materials_page()
elif page == "Important Topics":
    topics_page()
elif page == "FAQ":
    faq_page()
elif page == "Explain Simply":
    explain_page()
elif page == "Quiz":
    quiz_page()
elif page == "Search":
    search_page()
else:
    settings_page()
