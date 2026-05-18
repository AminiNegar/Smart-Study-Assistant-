from pypdf import  PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from groq import Groq
from dotenv import load_dotenv
import json 
from pydantic import BaseModel, Field
from typing import List
import sqlite3

#api key
load_dotenv()
client = Groq(api_key="GROQ_API_KEY")

# classes
class QuizItem(BaseModel):
    question: str = Field(description="The multiple-choice question in English")
    options: List[str] = Field(description="Exactly 4 options in English")
    answer: str = Field(description="The correct option text, matching one option exactly")

class FlashcardItem(BaseModel):
    front: str = Field(description="Concept or question in English")
    back: str = Field(description="Explanation or answer in English")


#database
DB_Name = 'study_assistant.db'

def init_db() :
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute(
        """ CREATE TABLE IF NOT EXISTS files(
        id INTEGER PRIMARY KEY AUTOINCREMENT , 
        filename   TEXT UNIQUE , 
        chunks TEXT , 
        summary TEXT , 
        quiz TEXT , 
        flashcards TEXT
        )
 """
    )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on script load
init_db()

#main functions 

def get_file_from_db(filename) :
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT chunks, summary, quiz, flashcards FROM files WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "chunks": json.loads(row[0]),
            "summary": row[1],
            "quiz": json.loads(row[2]) if row[2] else None,
            "flashcards": json.loads(row[3]) if row[3] else None
        }
    return None

# ---- DB Helper Functions ----
def save_file_to_db(filename, chunks, summary=None, quiz=None, flashcards=None):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO files (filename, chunks, summary, quiz, flashcards)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(filename) DO UPDATE SET
            chunks=excluded.chunks,
            summary=coalesce(excluded.summary, summary),
            quiz=coalesce(excluded.quiz, quiz),
            flashcards=coalesce(excluded.flashcards, flashcards)
    """, (filename, json.dumps(chunks), summary, json.dumps(quiz) if quiz else None, json.dumps(flashcards) if flashcards else None))
    conn.commit()
    conn.close()

def get_file_from_db(filename):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT chunks, summary, quiz, flashcards FROM files WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "chunks": json.loads(row[0]),
            "summary": row[1],
            "quiz": json.loads(row[2]) if row[2] else None,
            "flashcards": json.loads(row[3]) if row[3] else None
        }
    return None

def save_chat_message(filename, role, content):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (filename, role, content) VALUES (?, ?, ?)", (filename, role, content))
    conn.commit()
    conn.close()

def get_chat_history(filename):
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history WHERE filename = ? ORDER BY id ASC", (filename,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

#chat with pdf 
def chat_with_pdf(filename, chunks, user_question):
    """Finds relevant chunks and answers the user's question within the file context."""
    # Simple semantic search placeholder (filtering chunks containing keywords)
    keywords = user_question.lower().split()
    relevant_chunks = []
    for chunk in chunks:
        if any(kw in chunk.lower() for kw in keywords):
            relevant_chunks.append(chunk)
    
    # Fallback to first few chunks if no keyword match
    if not relevant_chunks:
        relevant_chunks = chunks[:3]
    
    context = "\n\n".join(relevant_chunks[:2])
    history = get_chat_history(filename)
    
    messages = [
        {"role": "system", "content": "You are a helpful study assistant. Answer the user's question strictly using the provided document context. If the answer cannot be found in the context, use your general knowledge but mention it is not explicitly in the document. Keep answers clear, factual, and in English."}
    ]
    # Append historical messages for context window awareness
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": f"Context from PDF:\n{context}\n\nQuestion: {user_question}"})
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.5
    )
    
    answer = response.choices[0].message.content
    # Save to SQLite Database
    save_chat_message(filename, "user", user_question)
    save_chat_message(filename, "assistant", answer)
    return answer

def extract_text_from_pdf(pdf_path) :
    print('reading from file ...')
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages :
        text = page.extract_text()
        if text :
            full_text += text + "\n"
    return full_text

def split_text_into_chunks(text) :
    print('converting text to chunks ... ')
    text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1500 , 
    chunk_overlap = 200 , 
    length_function = len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def generate_summary_for_chunk(chunk):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[
            {"role": "system", "content": "Provide a dense, concise summary of the text, keeping core facts."},
            {"role": "user", "content": chunk}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

def generate_final_summary(chunks, filename):
    cached = get_file_from_db(filename)
    if cached and cached.get("summary"):
        return cached["summary"]

    intermediate_summaries = [generate_summary_for_chunk(c) for c in chunks[:6]]
    combined_text = "\n".join(intermediate_summaries)
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Synthesize the provided summaries into a fluent, well-structured final summary in English using markdown. Start directly with the content."},
            {"role": "user", "content": combined_text}
        ],
        temperature=0.4
    )
    summary = response.choices[0].message.content
    save_file_to_db(filename, chunks, summary=summary)
    return summary

def generate_quiz(text_chunks, filename, num_questions=3):
    cached = get_file_from_db(filename)
    if cached and cached.get("quiz"):
        return cached["quiz"]

    context = "\n".join(text_chunks[:3])
    prompt = f"Generate {num_questions} multiple-choice questions in English based on this text. Return a strict JSON array matching the required schema."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a quiz generator. Output a raw JSON array of objects with keys: 'question', 'options' (array of 4 strings), and 'answer'."},
            {"role": "user", "content": f"Context:\n{context}\n\nPrompt: {prompt}"}
        ],
        temperature=0.4,
        response_format={"type": "json_object"}
    )
    
    try:
        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        items = data if isinstance(data, list) else data.get("questions", data.get("quiz", []))
        if not items and isinstance(data, dict):
            items = [data] if "question" in data else list(data.values())[0]

        validated_quiz = [QuizItem(**item).model_dump() for item in items[:num_questions]]
        save_file_to_db(filename, text_chunks, quiz=validated_quiz)
        return validated_quiz
    except Exception as e:
        print(f"Quiz Validation failed: {e}")
        return None

def generate_flashcards(text_chunks, filename, num_cards=4):
    cached = get_file_from_db(filename)
    if cached and cached.get("flashcards"):
        return cached["flashcards"]

    context = "\n".join(text_chunks[:3])
    prompt = f"Generate {num_cards} flashcards in English. Return a strict JSON array matching the schema."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a study assistant. Output a raw JSON array of objects with keys: 'front' and 'back'."},
            {"role": "user", "content": f"Context:\n{context}\n\nPrompt: {prompt}"}
        ],
        temperature=0.5,
        response_format={"type": "json_object"}
    )
    
    try:
        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        items = data if isinstance(data, list) else data.get("flashcards", list(data.values())[0])
        
        validated_cards = [FlashcardItem(**item).model_dump() for item in items[:num_cards]]
        save_file_to_db(filename, text_chunks, flashcards=validated_cards)
        return validated_cards
    except Exception as e:
        print(f"Flashcard Validation failed: {e}")
        return None
if __name__ == "__main__":
    pdf_file_path = "sample.pdf" 
    
    # 1. Ingestion & Chunking
    raw_text = extract_text_from_pdf(pdf_file_path)
    print(f"Total characters extracted: {len(raw_text)}")
    
    chunks = split_text_into_chunks(raw_text)
    print(f"Total chunks created: {len(chunks)}")
    
    # 2. Pipeline Phase: Summarization (Map-Reduce)
    print("\n--- Running Summarization Pipeline ---")
    intermediate_summaries = [generate_summary_for_chunk(c) for c in chunks[:3]]
    final_summary = generate_final_summary(intermediate_summaries)
    
    print("\n================ FINAL SUMMARY ================\n")
    print(final_summary)
    print("================================================\n")
    
    # 3. Pipeline Phase: Quiz Generation
    print("\n--- Running Quiz Generation Pipeline ---")
    quiz_data = generate_quiz(chunks, num_questions=3)
    if quiz_data:
        print("\n================ GENERATED QUIZ ================\n")
        questions = quiz_data if isinstance(quiz_data, list) else quiz_data.get("questions", [])
        for idx, q in enumerate(questions):
            print(f"Q{idx+1}: {q['question']}")
            for o_idx, option in enumerate(q['options']):
                print(f"  {o_idx+1}) {option}")
            print(f"🎯 Answer: {q['answer']}\n")
        print("================================================\n")

    # 4. Pipeline Phase: Flashcard Generation
    print("\n--- Running Flashcard Generation Pipeline ---")
    flashcards_data = generate_flashcards(chunks, num_cards=4)
    if flashcards_data:
        print("\n================ GENERATED FLASHCARDS ================\n")
        cards = flashcards_data if isinstance(flashcards_data, list) else flashcards_data.get("flashcards", [])
        for idx, card in enumerate(cards):
            print(f"Card {idx+1}:")
            print(f"   [Front]: {card['front']}")
            print(f"   [Back] : {card['back']}\n")
        print("================================================\n")