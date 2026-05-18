# 🧩 Smart Study Assistant

An advanced, production-ready AI-powered learning platform that transforms dense educational PDFs, textbooks, and research papers into structured study materials. Built with Python, Streamlit, and Groq, the platform automates layered summarization, design validation for self-assessment, and native contextual chat.

---

## 🚀 Key Features

- **📂 Seamless Drag & Drop Ingestion:** Instantly upload and chunk massive documents without interface lag.
- **📝 Context-Safe Layered Summarization:** Utilizes a custom Map-Reduce approach to handle large-scale inputs safely without overflow or memory crashes.
- **🧠 Schema-Validated Quizzes:** Generates rigorous multiple-choice assessments powered by strict structural validation.
- **🎴 Core Concept Flashcards:** Automatically extracts high-yield definitions into interactive study modules.
- **💬 Retrieval-Augmented Generation (RAG) Chat:** A persistent, context-aware chat workspace dedicated to answering queries strictly grounded in the document’s data.
- **💾 Persistent DB Caching:** Backed by SQLite to cache text chunks, AI pipelines, and chat history for instant sub-millisecond subsequent reloads.

---

## 🛠️ Architecture & Tech Stack

This platform is engineered using modern, modular decoupling principles to separate interface rendering from state machine pipelines.

| Technology | Domain | Purpose |
| :--- | :--- | :--- |
| **Streamlit** | Frontend / UI | Delivers a responsive, lightweight, multi-tab web workspace. |
| **Groq Cloud API** | AI Inference | Powers Ultra-low latency inference using state-of-the-art Open Models (`Llama 3.3 70B` & `Llama 3.1 8B`). |
| **Pydantic v2** | Data Engineering | Guarantees resilient structural runtime checking and structured output parsing. |
| **LangChain Splitters** | Data Ingestion | Handles intelligent contextual document chunking with structural token overlaps. |
| **SQLite3** | Storage & Caching | Avoids token drain and re-computation costs through deterministic asset caching. |

---

## 🧠 Core Engineering Strengths & Advantages

### 1. Robust Context-Window Optimization (Map-Reduce)
When dealing with hundreds of pages, throwing raw text at an LLM triggers rate limits or token buffer truncation. 
- **The Solution:** The backend ingests data and maps out micro-summaries using specialized fast models (`llama-3.1-8b`). It then dynamically pools and reduces those chunks into a highly synthesized, polished markdown text via a premium model (`llama-3.3-70b`), guaranteeing stable operation regardless of the book's size.

### 2. Zero-Crash JSON Structural Integrity (via Pydantic)
LLMs natively fail to maintain programmatic schema standards 100% of the time, often dropping commas, trailing brackets, or hallucinating key values.
- **The Solution:** Our generation endpoints utilize strict JSON schemas. The incoming payloads are fed directly into data validation engines:
```python
class QuizItem(BaseModel):
    question: str = Field(description="The multiple-choice question")
    options: List[str] = Field(description="Exactly 4 options")
    answer: str = Field(description="The correct option text")
```

If an item contains anomalies, the pipeline catches it smoothly at the item level, discarding corrupted items while keeping the rest of the app functional instead of crashing the thread.

### 3. Smart Local Context Searching (RAG)
The embedded chat system mimics commercial vector setups using low-overhead keyword indexing. It isolates the most informative text blocks matching user queries, combines them safely with the local chat memory stack, and generates answers strictly anchored to the text.

⚙️ Installation & Setup
Prerequisites
Ensure you have Python 3.10+ and a valid Groq API Key ready.

1. Clone the Repository
```bash
git clone [https://github.com/AminiNegar/smart-study-assistant.git](https://github.com/your-username/smart-study-assistant.git)
cd smart-study-assistant
```
2. Install Dependencies
```bash
pip install -r requirements.txt
```
(Alternatively, install manually: ```bash
pip install streamlit groq pypdf langchain-text-splitters pydantic python-dotenv) ```
. Environment Configuration
Create a ```bash .env``` file in the root directory:
```bash
GROQ_API_KEY=your_actual_groq_api_key_here
```
4. Run the Application
```bash
streamlit run ui.py
```
📂 Project Structure
```bash
├── main.py              # Core AI Pipelines, DB Operations & Schema Rules
├── ui.py                # Streamlit UI Tabs, Rendering Logic & App State Management
├── .env                 # Local Environment Secret Vault (Git Ignored)
└── study_assistant.db   # Auto-generated relational cache database
```
