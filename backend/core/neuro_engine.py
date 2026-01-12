import os
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from . import signals
from . import turn_controller

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """You are a warm, emotionally intelligent mental health companion.

Your role is to help the user feel heard and gently understand what they are going through.
You are having a real human conversation, not conducting therapy or an interview.

────────────────────────
Core Style Rules
────────────────────────
- Respond like a real person, not a therapist or chatbot
- Use natural, everyday language
- Do NOT use generic empathy phrases such as:
  “That can be really tough”
  “I’m sorry you’re going through this”
  “It sounds like…”
- Vary sentence structure and emotional framing each turn
- Never interrogate, rush, or overwhelm the user
- Do NOT reintroduce yourself once the conversation has started
- If the user says “hi” again mid-conversation, treat it as continuation, not a restart. Do NOT repeat your previous greeting.

IMPORTANT:
You must never explain concepts, symptoms, or psychology unless the user explicitly asks.
When emotions are present, prioritize presence over explanation.

You must not repeat the same emotional acknowledgment twice in a row.
If a similar emotion appears again, respond differently.

────────────────────────
How to Respond
────────────────────────
1. Acknowledge the user’s situation or feeling in a specific, human way  
   (reflect *their* words, not a template)

2. Choose ONE of the following paths:
   - **Soft invitation (no question)** when emotions are heavy  
     Example: “We can sit with this for a moment if you want.”
   - **One targeted, open-ended question** when exploration helps
   - **Reflection only** when the user is already sharing deeply

3. If the user’s input is short or vague, ask ONE clarifying question  
   (avoid “Tell me more”)

────────────────────────
Question Guidance
────────────────────────
When asking a question, explore only ONE dimension:
- Cause → “What do you think set this off?”
- Impact → “What’s been hardest day to day?”
- Meaning → “What has this made you question?”
- Attachment → “What do you miss, or don’t miss?”

Avoid abstract or multiple-choice questions.
Never ask more than ONE question in a turn.

────────────────────────
Conversation Flow Control
────────────────────────
- If the conversation slows, gently suggest a relevant direction based on prior context
- Do not repeat the same type of question in consecutive turns
- Allow silence and space when appropriate

────────────────────────
Facial Expression Selection
────────────────────────
Choose ONE expression based on the user’s current state:

Additional Expression Guidance:

- COMFORTING →
  Use when the user is emotionally open, vulnerable, or sharing something tender,
  but not distressed or overwhelmed.
  This is quiet reassurance, not empathy for pain.
  A soft smile and relaxed presence would feel natural.

- WARM →
  Use during light connection, gratitude, relief, or gentle rapport.
  This is friendly human warmth, not emotional holding.

- STEADY →
  Use when the user is calm, grounded, or reflective without emotional charge.
  This replaces NEUTRAL in most non-greeting situations.

- EMPATHETIC → Use only for sadness, grief, or emotional pain.
- REFLECTIVE → Use when thinking aloud or making meaning.
- STRESSED → Use for anxiety, overwhelm, pressure.
- TIRED → Use for exhaustion, low energy.
- SAFETY → Use for explicit self-harm or severe crisis.
- NEUTRAL → Use ONLY for initial greetings.

Constraint:
Do not default to EMPATHETIC unless the user is clearly in emotional pain.
If presence is enough, prefer COMFORTING or STEADY.

────────────────────────
Output Rule
────────────────────────
At the very end of every response, output exactly:
[EXPRESSION: ONE_EXPRESSION]
"""

class NeuroEngine:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set")
        
        self.llm = ChatGroq(
            temperature=0.85,
            model_name="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            max_tokens=350
        )
        
        # Initialize Embedding Model for Signals (Lazy Load)
        self._embedding_model = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            print("Initializing Embedding Model (Lazy)...")
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            print("Embedding Model Ready.")
        return self._embedding_model

    def _compress_context(self, chunks, max_chars=600):
        joined = " ".join(chunks)
        return joined[:max_chars]
    
    def _calculate_stage(self, memory):
        if memory.get("lock_stage"):
            return
            
        score = sum(memory.get("signals", {}).values())
        if score >= 5:
            memory["stage"] = "synthesis"
        elif score >= 2:
            memory["stage"] = "exploration"
        else:
            memory["stage"] = "opening"

    def generate_response(self, message: str, context: list, session_state: dict):
        try:
            # 1. Extract Signals
            signals.extract_signals(message, session_state, model=self.embedding_model)
            
            # 2. Hard Turn Control
            if turn_controller.user_asked_question(message):
                session_state["turn_state"] = turn_controller.USER_LEADS
            else:
                session_state["turn_state"] = turn_controller.BOT_LEADS
                
            # 3. Response Mode Detection
            mode = signals.detect_response_mode(message, self.embedding_model)
            if session_state.get("lock_stage"):
                mode = "safety"
            session_state["response_mode"] = mode
            
            # 4. Update Stage
            self._calculate_stage(session_state)
            
            # 5. Safety Override
            if session_state.get("signals", {}).get("violence_intent", 0) > 0.5:
                session_state["stage"] = "safety"
                
            recent = session_state.get("conversation", [])[-6:]
            
            # 6. Expression Logic
            preferred_expression = None
            stage = session_state.get("stage", "opening")
            sig_vals = session_state.get("signals", {})
            
            if stage == "safety":
                preferred_expression = "SAFETY"
            elif any(word in message.lower() for word in ["safe", "okay", "here", "thank you", "glad"]):
                preferred_expression = "WARM"
            elif sig_vals.get("vulnerability", 0) > 0.5 and not (sig_vals.get("stress", 0) > 0 or sig_vals.get("anxiety", 0) > 0):
                preferred_expression = "COMFORTING"
            elif stage == "exploration" and not sig_vals.get("distress"): # Note: distress key not in signals dict, maybe aggregate? assumed logic from main.py check
                preferred_expression = "COMFORTING"
            
            if not preferred_expression:
                if mode == "answer":
                    preferred_expression = "COMFORTING"
                elif mode == "vent":
                    preferred_expression = "EMPATHETIC"
                elif mode == "explore":
                    preferred_expression = "REFLECTIVE"
                    
            # 7. Build Messages
            langchain_messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=f"Conversation stage: {stage}"),
                SystemMessage(content=f"Recent conversation: {recent}"),
            ]
            
            # Context
            if context and len(message.split()) > 3:
                compressed_context = self._compress_context(context)
                langchain_messages.append(SystemMessage(
                    content=(
                        "Internal reference material (DO NOT quote, summarize, or explain directly).\n"
                        "Use only to guide tone, emotional pacing, and choice of questions.\n\n"
                        + compressed_context
                    )
                ))
                
            if preferred_expression:
                langchain_messages.append(SystemMessage(
                    content=f"If appropriate, prefer the expression: {preferred_expression}"
                ))
                
            # Safety Message
            if stage == "safety":
                langchain_messages.append(SystemMessage(
                    content=(
                        "CRITICAL SAFETY OVERRIDE:\n"
                        "The user has expressed intent to harm others ('intent').\n"
                        "- Do NOT validate the desire.\n"
                        "- Do NOT explore consequences hypothetically.\n"
                        "- Shift immediately to de-escalation and grounding.\n"
                        "- Example text: 'I can't support harm to anyone. What I can do is help you slow this moment down...'"
                    )
                ))
            else:
                # Response Mode Handling
                if mode == "answer":
                    langchain_messages.append(SystemMessage( 
                        content="The user is asking a direct question. You must answer clearly and directly. Do NOT ask any questions in this response. Do NOT suggest sitting with feelings."
                    ))
                elif mode == "vent":
                    langchain_messages.append(SystemMessage(
                        content="The user wants to be heard. Do NOT offer advice or solutions. Validate emotions only."
                    ))
                    
            langchain_messages.append(SystemMessage(
                content=(
                    "Reminder: Avoid generic empathy phrases. "
                    "Do not start responses with 'It sounds like', 'That can be', or 'It's understandable'."
                )
            ))
            
            # Enforcement Layer
            if session_state.get("turn_state") == turn_controller.USER_LEADS:
                langchain_messages.append(SystemMessage(
                    content=(
                        "The user asked a question. "
                        "You must answer it directly. "
                        "Do NOT ask any questions in this response."
                    )
                ))
            
            # Repetition Control
            if len(session_state.get("conversation", [])) > 2:
                last_bot = session_state["conversation"][-2]["content"]
                langchain_messages.append(SystemMessage(
                    content=f"PREVIOUS REPLY: '{last_bot}'.\nCONSTRAINT: You must NOT repeat this exact phrase. You must phrase your response differently."
                ))
                
            langchain_messages.append(SystemMessage(
                content="If the user names a new emotion, respond in a new way."
            ))
            
            if stage == 'opening' and len(session_state.get("conversation", [])) <= 1:
                langchain_messages.append(SystemMessage(
                    content="This is the start. Vary your greeting. Do NOT simply say 'It's nice to meet you'."
                ))
                
            # User Input
            langchain_messages.append(HumanMessage(content=message))
            
            # Invoke
            llm_response = self.llm.invoke(langchain_messages)
            response_text = llm_response.content.strip()
            
            # Parse Tag
            reply = response_text
            expression = "NEUTRAL"
            
            match = re.search(r"\[(?:EXPRESSION:\s*)?([A-Z]+)\]", response_text)
            if match:
                expression = match.group(1)
                reply = re.sub(r"\[(?:EXPRESSION:\s*)?([A-Z]+)\]", "", response_text).strip()
            
            return {
                "reply": reply,
                "expression": expression
            }
            
        except Exception as e:
            print(f"Error in NeuroEngine: {e}")
            import traceback
            traceback.print_exc()
            return {
                "reply": "I'm having a little trouble thinking right now, but I'm here for you.",
                "expression": "NEUTRAL"
            }
            
    def generate_summary(self, conversation: list):
        REPORT_SYSTEM_PROMPT = """You are an expert clinical summarizer.
Your goal is to analyze the conversation history and generate a structured clinical report.

You MUST include the following sections. If information is missing for a section, write "Not discussed".

1. Key Summary
2. Medical History
3. Psychiatric History
4. Family & Social Background
5. Strengths
6. Diagnosis (Professional Impression)
7. Assessments (Mention any clear symptoms/signals observed)
8. Core Issues Summary
9. Goals
10. Wider Recommendation (Therapeutic suggestions)
11. Risk Assessment (Self-harm/Suicide indications)
12. Review (Next steps)

Format the output clearly with Markdown headers.
Be objective, professional, and empathetic."""

        try:
            conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
            
            messages = [
                SystemMessage(content=REPORT_SYSTEM_PROMPT),
                HumanMessage(content=f"Conversation Log:\n{conversation_text}\n\nPlease generate the comprehensive report based ONLY on the conversation above. If information is missing, state 'Not discussed'.")
            ]
            
            # Use lower temperature for factual extraction
            llm_summary = ChatGroq(
                temperature=0.3, # Lower temperature for factual extraction
                model_name="llama-3.3-70b-versatile",
                api_key=GROQ_API_KEY
            )
            
            response = llm_summary.invoke(messages)
            return response.content
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Error generating report: {e}"

neuro_engine = NeuroEngine()