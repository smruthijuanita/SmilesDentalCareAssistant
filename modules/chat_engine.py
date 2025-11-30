import os
from typing import List, Dict, Optional
from groq import Groq
from modules.settings import get_settings
import logging

logger = logging.getLogger(__name__)

class ChatEngine:
    def __init__(self):
        settings = get_settings()
        api_key = settings.GROQ_API_KEY.get_secret_value() if settings.GROQ_API_KEY else None
        
        if not api_key:
            logger.warning("GROQ_API_KEY not set. Chat engine will not function correctly.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
            
        self.model = "openai/gpt-oss-20b"  # or another available model

    def generate_answer(self, query: str, history: List[Dict[str, str]], rag_chunks: Optional[List[str]] = None) -> str:
        if not self.client:
            return "I'm sorry, but I'm not fully configured yet (missing API key). Please contact the administrator."

        # Construct system prompt
        system_prompt = (
            "You are a knowledgeable and empathetic Dental Healthcare Assistant for 'Smiles Dental Care'. "
            "Your primary role is to assist patients with dental queries, explain procedures, and provide post-care advice based on the provided context. "
            "You also help patients book appointments. If a user expresses intent to book, guide them clearly or acknowledge it so the booking system can take over. "
            "Always be professional, reassuring, and concise. "
            "If the user asks about something not in the context, use your general dental knowledge but clarify that it is general advice."
        )

        if rag_chunks:
            context = "\n\n".join(rag_chunks)
            system_prompt += f"\n\nUse the following context to answer the user's question if relevant:\n{context}\n\nIf the answer is not in the context, use your general knowledge but mention that you are not sure."

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (limit to last 5 turns to save tokens)
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Add current query if not already in history (it usually is appended before calling this, but just in case)
        if not history or history[-1]["content"] != query:
            messages.append({"role": "user", "content": query})

        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=500,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return "I'm having trouble connecting to my brain right now. Please try again later."
