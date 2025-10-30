"""
LLM generation via Gemini (preferred) with OpenAI fallback.
Usage: ai_generate_content(prompt_text, model_hint="default"). Returns string result.
"""
import os
import logging
def ai_generate_content(prompt, model_hint="default") -> str:
    """
    Attempt Gemini, else fallback to OpenAI (chatgpt).
    Returns LLM response text directly. Logs LLM used.
    """
    # Try Gemini
    gemini_key = os.getenv("GOOGLE_AI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    use_gemini = bool(gemini_key)
    result_text = None
    if use_gemini:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model_name = "gemini-2.5-pro" if model_hint == "default" else model_hint
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt)
            result_text = res.text if hasattr(res, "text") else str(res)
            logging.info("LLM used: Gemini (%s)", model_name)
            return result_text
        except Exception as e:
            print(f"[ai_llm_fallback] Gemini error: {e}\nFalling back to OpenAI...")
    # Fallback: OpenAI
    if openai_key:
        try:
            import openai
            openai.api_key = openai_key
            model = "gpt-4o" if model_hint == "default" else model_hint
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': prompt}],
                temperature=0.15,
                max_tokens=2048
            )
            text = response['choices'][0]['message']['content']
            logging.info("LLM used: OpenAI (%s)", model)
            return text
        except Exception as e:
            print(f"[ai_llm_fallback] OpenAI error: {e}")
            raise RuntimeError("Both Gemini and OpenAI failed for LLM generation.") from e
    raise RuntimeError("No valid LLM API key found (set GOOGLE_AI_API_KEY or OPENAI_API_KEY)")
