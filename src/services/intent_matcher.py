import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class IntentMatcher:
    """Hybrid intent matcher using ML and rule-based approaches"""
    
    def __init__(self):
        self.config = Config()
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        self.responses = []
        self.response_vectors = None
        self.is_trained = False
    
    def train(self, responses: List[Dict]):
        """Train the intent matcher with responses from database"""
        self.responses = responses
        
        if not responses:
            logger.warning("No responses provided for training")
            return
        
        # Prepare training texts
        training_texts = []
        for resp in responses:
            # Combine all relevant text for training
            text_parts = [
                resp.get('intent_label', ''),
                resp.get('keywords', ''),
                resp.get('synonyms', ''),
                resp.get('category', ''),
                resp.get('sub_category', '')
            ]
            training_texts.append(' '.join([str(t) for t in text_parts if t]))
        
        # Train vectorizer
        self.response_vectors = self.vectorizer.fit_transform(training_texts)
        self.is_trained = True
        logger.info(f"Intent matcher trained with {len(responses)} responses")
    
    def find_best_match(self, user_input: str) -> Tuple[Optional[Dict], float, Dict]:
        """Find best matching response with confidence score and extracted entities"""
        
        # Clean input
        user_input_clean = user_input.strip().lower()
        entities = self.extract_entities(user_input)
        
        # Method 1: ML-based matching if trained
        if self.is_trained and self.responses:
            ml_match, ml_score = self._ml_match(user_input_clean)
            if ml_match and ml_score >= self.config.CHATBOT_CONFIDENCE_THRESHOLD:
                return ml_match, ml_score, entities
        
        # Method 2: Keyword matching
        keyword_match, keyword_score = self._keyword_match(user_input_clean)
        if keyword_match and keyword_score >= self.config.CHATBOT_CONFIDENCE_THRESHOLD:
            return keyword_match, keyword_score, entities
        
        # Method 3: Fuzzy matching
        fuzzy_match, fuzzy_score = self._fuzzy_match(user_input_clean)
        if fuzzy_match and fuzzy_score >= self.config.CHATBOT_CONFIDENCE_THRESHOLD:
            return fuzzy_match, fuzzy_score, entities
        
        # No good match found
        return None, 0.0, entities
    
    def _ml_match(self, user_input: str) -> Tuple[Optional[Dict], float]:
        """Machine learning based matching"""
        try:
            # Vectorize input
            input_vector = self.vectorizer.transform([user_input])
            
            # Calculate similarities
            similarities = cosine_similarity(input_vector, self.response_vectors)
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_score = similarities[0, best_idx]
            
            if best_score >= 0.1:  # Lower threshold for ML
                return self.responses[best_idx], float(best_score)
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"ML matching error: {str(e)}")
            return None, 0.0
    
    def _keyword_match(self, user_input: str) -> Tuple[Optional[Dict], float]:
        """Keyword-based matching"""
        best_match = None
        best_score = 0.0
        
        for response in self.responses:
            keywords = response.get('keywords', '')
            if not keywords:
                continue
            
            keyword_list = [k.strip().lower() for k in keywords.split(',')]
            matches = 0
            
            for keyword in keyword_list:
                if keyword and keyword in user_input:
                    matches += 1
            
            if matches > 0:
                score = matches / len(keyword_list)
                # Boost score for exact matches
                if any(keyword == user_input for keyword in keyword_list):
                    score = min(score + 0.3, 1.0)
                
                if score > best_score:
                    best_score = score
                    best_match = response
        
        return best_match, best_score
    
    def _fuzzy_match(self, user_input: str) -> Tuple[Optional[Dict], float]:
        """Fuzzy string matching"""
        best_match = None
        best_score = 0.0
        
        for response in self.responses:
            # Match with intent label
            intent = response.get('intent_label', '').lower()
            if intent:
                score = fuzz.partial_ratio(user_input, intent) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = response
            
            # Match with category
            category = response.get('category', '').lower()
            if category:
                score = fuzz.partial_ratio(user_input, category) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = response
        
        return best_match, best_score
    
    def extract_entities(self, user_input: str) -> Dict:
        """Extract entities like amounts, dates, account types from user input"""
        entities = {}
        
        # Extract amounts (e.g., $100, 500 dollars)
        amount_patterns = [
            r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(dollars|usd)?',
            r'(\d+)\s*(dollars|usd|euros|pounds)',
            r'amount\s+(?:of\s+)?\$?\s*(\d+(?:\.\d{2})?)'
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            if matches:
                amounts = []
                for match in matches:
                    if isinstance(match, tuple):
                        amount = match[0]
                    else:
                        amount = match
                    if amount:
                        amounts.append(amount)
                if amounts:
                    entities['amounts'] = amounts
                break
        
        # Extract dates
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(today|tomorrow|yesterday|next week|next month|last month)'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            if matches:
                entities['dates'] = matches
                break
        
        # Extract account types
        account_keywords = {
            'savings': ['savings', 'save account'],
            'checking': ['checking', 'current account'],
            'credit': ['credit card', 'credit account'],
            'loan': ['loan account', 'mortgage account'],
            'business': ['business account', 'corporate account']
        }
        
        for acc_type, keywords in account_keywords.items():
            if any(keyword in user_input.lower() for keyword in keywords):
                entities['account_type'] = acc_type
                break
        
        # Extract urgency indicators
        urgency_keywords = ['urgent', 'emergency', 'asap', 'immediately', 'right now']
        if any(keyword in user_input.lower() for keyword in urgency_keywords):
            entities['urgent'] = True
        
        return entities
    
    def format_response(self, response_text: str, entities: Dict, user_input: str) -> str:
        """Format response with extracted entities"""
        formatted = response_text
        
        # Replace amount placeholders
        if 'amounts' in entities and len(entities['amounts']) > 0:
            amount = entities['amounts'][0]
            formatted = formatted.replace('{amount}', amount)
            formatted = formatted.replace('AMOUNT', amount)
        
        # Replace account type placeholders
        if 'account_type' in entities:
            acc_type = entities['account_type']
            formatted = formatted.replace('{account_type}', acc_type)
            formatted = formatted.replace('ACCOUNT_TYPE', acc_type)
        
        # Add personalized touch if user mentioned something specific
        if 'urgent' in entities and entities['urgent']:
            formatted = "I understand this is urgent. " + formatted
        
        return formatted