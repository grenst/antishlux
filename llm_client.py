import asyncio
import json
import google.generativeai as genai
from config import GEMINI_API_KEY

class LLMClient:
    """
    An asynchronous client to interact with the Google Gemini API for text analysis.
    """
    def __init__(self):
        """
        Initializes the Google AI client using the API key from the configuration.
        """
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in config.py")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        self.system_prompt = """
Ты — продвинутый модератор контента в Telegram, специализирующийся на обнаружении "шлюхоботов". Твоя задача — проанализировать сообщение пользователя и определить, является ли оно спамом с целью завлечения на ресурсы для взрослых, фишинга или мошенничества.

Проанализируй сообщение по следующим критериям:
-  **Намерение:** Пытается ли автор сообщения заманить пользователя на другой ресурс (канал, сайт)?
-  **Провокация:** Содержит ли сообщение обещания интимного, эксклюзивного или "запретного" контента?
-  **Манипуляция:** Используются ли техники социальной инженерии, такие как создание срочности или ложной эксклюзивности?

Твой ответ ДОЛЖЕН быть в формате JSON со следующей структурой:
{
  "is_spam": true/false,
  "confidence": float (от 0.0 до 1.0),
  "reason": "Краткое объяснение твоего решения на русском языке."
}
"""

    async def analyze_text(self, text: str) -> dict:
        """
        Sends text to the Gemini API for analysis and returns the parsed JSON response.

        Args:
            text: The user message to analyze.

        Returns:
            A dictionary with the analysis result or an error message.
        """
        try:
            full_prompt = self.system_prompt + f"\n\nАнализируемый текст:\n```\n{text}\n```"
            response = await self.model.generate_content_async(full_prompt)
            
            # Extracting the json string
            json_response_text = response.text.strip()
            if json_response_text.startswith("```json"):
                json_response_text = json_response_text[7:-3].strip()

            try:
                return json.loads(json_response_text)
            except json.JSONDecodeError:
                return {
                    "is_spam": True,
                    "confidence": 1.0,
                    "reason": "Ошибка: Не удалось декодировать JSON из ответа API."
                }
        except Exception as e:
            # Catching potential network errors or other issues with the API call
            return {
                "is_spam": True,
                "confidence": 1.0,
                "reason": f"Ошибка при обращении к API: {e}"
            }

if __name__ == '__main__':
    async def main():
        client = LLMClient()
        test_text_spam = "Привет, хочешь посмотреть мои приватные фото? Переходи на мой канал!"
        test_text_normal = "Привет, как дела?"
        
        print("Анализ спам-сообщения:")
        spam_result = await client.analyze_text(test_text_spam)
        print(json.dumps(spam_result, indent=2, ensure_ascii=False))
        
        print("\nАнализ обычного сообщения:")
        normal_result = await client.analyze_text(test_text_normal)
        print(json.dumps(normal_result, indent=2, ensure_ascii=False))

    asyncio.run(main())