"""
LLM client for analyzing text messages using Google Gemini API.
Detects spam, inappropriate content, and provides analysis results.
"""

import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY

# Set up logging
logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with Google Gemini LLM API to analyze text messages.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the LLM client.
        
        Args:
            api_key: Google Gemini API key. If not provided, uses config.GEMINI_API_KEY
        """
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-pro')
        
        logger.info("LLM client initialized successfully")
    
    def _create_analysis_prompt(self, text: str) -> str:
        """
        Create a structured prompt for text analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            str: Formatted prompt for the LLM
        """
        prompt = f"""
Проанализируй следующее сообщение на предмет спама, нарушений и неподобающего контента.

Текст для анализа: "{text}"

Верни результат строго в JSON формате:
{{
    "is_spam": boolean,
    "spam_confidence": float (0.0-1.0),
    "violation_types": ["type1", "type2"],
    "is_appropriate": boolean,
    "reason": "краткое объяснение решения",
    "suggested_action": "approve/warn/ban"
}}

Категории нарушений:
- "adult_content" - контент для взрослых, эротика
- "financial_spam" - финансовые схемы, инвестиции, заработок
- "advertisement" - реклама товаров/услуг
- "phishing" - подозрительные ссылки, фишинг
- "harassment" - оскорбления, угрозы
- "crypto_spam" - криптовалюты, майнинг
- "mlm" - сетевой маркетинг, пирамиды

Анализируй только содержание, игнорируй грамматические ошибки.
"""
        return prompt.strip()
    
    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze text message using LLM API.
        
        Args:
            text: Text message to analyze
            
        Returns:
            Dict containing analysis results
            
        Raises:
            ValueError: If text is empty or API key is invalid
            RuntimeError: If API request fails
            json.JSONDecodeError: If response is not valid JSON
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            # Create prompt
            prompt = self._create_analysis_prompt(text)
            logger.debug(f"Generated prompt for text analysis: {prompt[:100]}...")
            
            # Make API request
            response = await self._make_api_request(prompt)
            
            # Parse and validate response
            result = self._parse_response(response)
            
            logger.info(f"Text analysis completed: spam={result.get('is_spam')}, "
                       f"confidence={result.get('spam_confidence')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            raise
    
    async def _make_api_request(self, prompt: str) -> str:
        """
        Make API request to Gemini.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            str: Raw response from the API
            
        Raises:
            RuntimeError: If API request fails
        """
        try:
            # Generate response
            response = await self.model.generate_content_async(prompt)
            
            if not response.text:
                raise RuntimeError("Empty response from Gemini API")
            
            logger.debug(f"Received API response: {response.text[:200]}...")
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            raise RuntimeError(f"Failed to get response from Gemini API: {e}")
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate LLM response.
        
        Args:
            response_text: Raw response from the API
            
        Returns:
            Dict: Parsed and validated response
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If response doesn't contain required fields
        """
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Sometimes the model wraps JSON in markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = [
                'is_spam', 'spam_confidence', 'violation_types', 
                'is_appropriate', 'reason', 'suggested_action'
            ]
            
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate data types and ranges
            if not isinstance(result['is_spam'], bool):
                raise ValueError("is_spam must be boolean")
            
            if not isinstance(result['spam_confidence'], (int, float)):
                raise ValueError("spam_confidence must be a number")
            
            if not (0.0 <= result['spam_confidence'] <= 1.0):
                raise ValueError("spam_confidence must be between 0.0 and 1.0")
            
            if not isinstance(result['violation_types'], list):
                raise ValueError("violation_types must be a list")
            
            if not isinstance(result['is_appropriate'], bool):
                raise ValueError("is_appropriate must be boolean")
            
            if result['suggested_action'] not in ['approve', 'warn', 'ban']:
                raise ValueError("suggested_action must be 'approve', 'warn', or 'ban'")
            
            logger.debug("Response validation successful")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response_text}")
            raise json.JSONDecodeError(f"Invalid JSON in LLM response: {e}", response_text, 0)
        
        except ValueError as e:
            logger.error(f"Response validation failed: {e}")
            raise
    
    def get_fallback_analysis(self, text: str) -> Dict[str, Any]:
        """
        Provide fallback analysis when LLM is unavailable.
        Uses simple keyword matching as backup.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict: Basic analysis result
        """
        from config import STOP_WORDS
        
        text_lower = text.lower()
        found_keywords = [word for word in STOP_WORDS if word in text_lower]
        
        is_spam = len(found_keywords) > 0
        confidence = min(len(found_keywords) * 0.3, 1.0)
        
        return {
            'is_spam': is_spam,
            'spam_confidence': confidence,
            'violation_types': ['keyword_match'] if is_spam else [],
            'is_appropriate': not is_spam,
            'reason': f'Keyword-based analysis. Found: {found_keywords}' if is_spam else 'No suspicious keywords found',
            'suggested_action': 'warn' if is_spam else 'approve'
        }
