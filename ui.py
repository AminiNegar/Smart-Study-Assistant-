import streamlit as st
import os
from main import (
    extract_text_from_pdf, 
    split_text_into_chunks, 
    generate_final_summary, 
    generate_quiz, 
    generate_flashcards,
    get_file_from_db,
    save_file_to_db,
    chat_with_pdf,
    get_chat_history
)

st.set_page_config(page_title="Smart Study Assistant", page_icon="🧩", layout="wide")

st.markdown("""
    <style>
    .stMarkdown, p, li { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .flashcard-box {
        background-color: #f8fafc;
        padding: 20px;
        border-radius: 8px;
        border-left: 5px solid #3b82f6;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧩 Smart Study Assistant")
st.subheader("Upload your PDF document to generate summaries, quizzes, flashcards, and chat natively!")

uploaded_file = st.file_uploader("Drop your lecture notes, essays, or textbook PDFs here", type=["pdf"])

if uploaded_file is not None:
    filename = uploaded_file.name
    temp_path = f"temp_{filename}"
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    # Check Database first before processing to enable instant load
    cached_data = get_file_from_db(filename)
    
    if "current_file" not in st.session_state or st.session_state["current_file"] != filename:
        if cached_data:
            st.session_state["chunks"] = cached_data["chunks"]
            if cached_data["summary"]: st.session_state["summary"] = cached_data["summary"]
            if cached_data["quiz"]: st.session_state["quiz"] = cached_data["quiz"]
            if cached_data["flashcards"]: st.session_state["flashcards"] = cached_data["flashcards"]
            st.success("🎯 Loaded instantly from Database cache!")
        else:
            with st.spinner("First time processing: Extracting text and chunking safely..."):
                raw_text = extract_text_from_pdf(temp_path)
                chunks = split_text_into_chunks(raw_text)
                st.session_state["chunks"] = chunks
                save_file_to_db(filename, chunks)
                st.session_state.pop("summary", None)
                st.session_state.pop("quiz", None)
                st.session_state.pop("flashcards", None)
            st.success("✅ File successfully processed and saved to DB!")
            
        st.session_state["current_file"] = filename

    chunks = st.session_state["chunks"]
    
    # 4 Navigation Tabs instead of 3
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Summary", "🧠 Quiz", "🎴 Flashcards", "💬 Chat with PDF"])
    
    # --- Tab 1: Summarization ---
    with tab1:
        st.header("Comprehensive Summary")
        if "summary" not in st.session_state:
            if st.button("Generate AI Summary"):
                with st.spinner("Synthesizing context-safe layer summaries..."):
                    st.session_state["summary"] = generate_final_summary(chunks, filename)
        
        if "summary" in st.session_state and st.session_state["summary"]:
            st.markdown(st.session_state["summary"])

    # --- Tab 2: Quiz Generation ---
    with tab2:
        st.header("Self-Assessment Quiz")
        if "quiz" not in st.session_state:
            if st.button("Design Structured Quiz"):
                with st.spinner("Generating and validating quiz schema..."):
                    st.session_state["quiz"] = generate_quiz(chunks, filename, num_questions=3)
                
        if "quiz" in st.session_state and st.session_state["quiz"]:
            for idx, q in enumerate(st.session_state["quiz"]):
                st.markdown(f"### **Question {idx+1}:** {q['question']}")
                user_ans = st.radio(f"Select your answer for Question {idx+1}:", q['options'], key=f"ans_{idx}", label_visibility="collapsed")
                
                if st.button(f"Submit Answer for Q{idx+1}", key=f"btn_{idx}"):
                    if user_ans == q['answer']:
                        st.success("🎉 Correct! Great job.")
                    else:
                        st.error(f"❌ Incorrect. The right answer is: {q['answer']}")
                st.markdown("---")

    # --- Tab 3: Flashcard Generation ---
    with tab3:
        st.header("Study Flashcards")
        if "flashcards" not in st.session_state:
            if st.button("Extract Flashcards"):
                with st.spinner("Extracting high-yield core concepts..."):
                    st.session_state["flashcards"] = generate_flashcards(chunks, filename, num_cards=4)
                
        if "flashcards" in st.session_state and st.session_state["flashcards"]:
            for idx, card in enumerate(st.session_state["flashcards"]):
                with st.expander(f"🎴 Card {idx+1}: {card['front']}"):
                    st.info(card['back'])

    # --- Tab 4: Chat with PDF (NEW) ---
    with tab4:
        st.header(f"💬 Chatting with: {filename}")
        st.write("Ask any question regarding the contents of this document.")
        
        # Display persistent history from Database
        chat_history = get_chat_history(filename)
        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # Accept user input
        if user_query := st.chat_input("Ask something about this book..."):
            with st.chat_message("user"):
                st.write(user_query)
                
            with st.chat_message("assistant"):
                with st.spinner("Searching PDF context..."):
                    response = chat_with_pdf(filename, chunks, user_query)
                    st.write(response)
            st.rerun() # Refresh layout to cleanly embed history

    if os.path.exists(temp_path):
        os.remove(temp_path)