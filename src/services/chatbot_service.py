import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
from src.database import DatabaseManager
from src.services.intent_matcher import IntentMatcher
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class ChatbotService:
    """Main chatbot service handling all chat operations"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatbotService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.config = Config()
        self.db = DatabaseManager()
        self.intent_matcher = IntentMatcher()
        
        # Initialize database
        self.db.initialize_tables()
        self.db.seed_default_responses()
        
        # Load responses from database
        self._load_responses()
        
        logger.info("Chatbot service initialized")
    
    def _load_responses(self):
        """Load responses from database"""
        try:
            query = """
            SELECT response_id, intent_label, response_text, keywords, 
                   synonyms, category, sub_category, priority, is_active
            FROM chatbot_responses 
            WHERE is_active = 1
            ORDER BY priority, intent_label
            """
            
            responses = self.db.pool.execute_query(query)
            
            if responses:
                self.intent_matcher.train(responses)
                logger.info(f"Loaded {len(responses)} active responses from database")
            else:
                logger.warning("No active responses found in database")
                
        except Exception as e:
            logger.error(f"Failed to load responses: {str(e)}")
            raise
    
    def process_message(self, user_message: str, session_id: str = None, 
                       customer_id: str = None, context: Dict = None) -> Dict:
        """Process user message and return bot response"""
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Validate input
        if not user_message or not user_message.strip():
            return self._create_error_response(
                session_id, 
                "I didn't receive any message. How can I help you today?",
                "empty_input"
            )
        
        user_message_clean = user_message.strip()
        
        try:
            # Find best matching response
            best_match, confidence, entities = self.intent_matcher.find_best_match(
                user_message_clean
            )
            
            # Generate response
            if best_match and confidence >= self.config.CHATBOT_CONFIDENCE_THRESHOLD:
                # Format response with entities
                response_text = self.intent_matcher.format_response(
                    best_match['response_text'],
                    entities,
                    user_message_clean
                )
                
                intent_label = best_match['intent_label']
                category = best_match.get('category', 'general')
                
            else:
                # Default response for unknown queries
                response_text = self.config.CHATBOT_DEFAULT_RESPONSE.format(
                    query=user_message_clean
                )
                intent_label = "unknown"
                confidence = 0.0
                category = "general"
            
            # Get suggestions for follow-up questions
            suggestions = self._get_suggestions(intent_label, category)
            
            # Log the interaction
            log_id = self._log_interaction(
                session_id=session_id,
                customer_id=customer_id,
                user_message=user_message_clean,
                bot_response=response_text,
                intent_label=intent_label,
                confidence_score=confidence,
                entities=entities,
                context=context
            )
            
            # Prepare response
            response = {
                'session_id': session_id,
                'response': response_text,
                'intent': intent_label,
                'category': category,
                'confidence': float(confidence),
                'entities': entities,
                'suggestions': suggestions,
                'log_id': log_id,
                'timestamp': datetime.now().isoformat()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return self._create_error_response(
                session_id,
                "I'm experiencing technical difficulties. Please try again in a moment.",
                "system_error"
            )
    
    def _log_interaction(self, session_id: str, customer_id: str, user_message: str,
                        bot_response: str, intent_label: str, confidence_score: float,
                        entities: Dict, context: Dict = None) -> Optional[int]:
        """Log chat interaction to database"""
        try:
            metadata = {
                'entities': entities,
                'context': context or {},
                'timestamp': datetime.now().isoformat()
            }
            
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            query = """
            INSERT INTO chatbot_chat_logs 
            (session_id, customer_id, user_message, bot_response, 
             intent_label, confidence_score, metadata)
            OUTPUT INSERTED.log_id
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            result = self.db.pool.execute_query(
                query,
                (session_id, customer_id, user_message[:2000], bot_response[:2000],
                 intent_label, confidence_score, metadata_json),
                fetch=True
            )
            
            if result and len(result) > 0:
                return result[0]['log_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to log interaction: {str(e)}")
            return None
    
    def _get_suggestions(self, current_intent: str, category: str) -> List[str]:
        """Get suggested follow-up questions"""
        
        suggestions_map = {
            'account_balance': ["How to transfer money?", "View transaction history", "Set up account alerts"],
            'account_statement': ["Download statement PDF", "Request statement by email", "Statement period selection"],
            'loan_inquiry': ["Check eligibility", "Interest rates", "Required documents", "Apply online"],
            'branch_locations': ["Working hours", "ATM locations", "Make appointment", "Services available"],
            'customer_support': ["Live chat", "Email support", "Phone callback", "Visit branch"],
            'transfer_funds': ["Transfer limits", "Schedule transfer", "International transfer", "Beneficiary management"],
            'card_issues': ["Report lost card", "Block card", "Request replacement", "Check card status"],
            'online_banking': ["Reset password", "App download", "Security features", "Mobile banking"]
        }
        
        # Get category-based suggestions
        category_suggestions = {
            'Account': ["Account balance", "Statements", "Transfers", "Account settings"],
            'Loans': ["Personal loan", "Home loan", "Car loan", "Loan calculator"],
            'Cards': ["Card activation", "Lost card", "Credit limit", "Rewards"],
            'Digital': ["Online banking", "Mobile app", "Security", "Digital wallet"]
        }
        
        # Combine suggestions
        suggestions = suggestions_map.get(current_intent, [])
        category_suggestions_list = category_suggestions.get(category, [])
        
        # Return unique suggestions (max 4)
        all_suggestions = list(set(suggestions + category_suggestions_list))
        return all_suggestions[:4]
    
    def get_chat_history(self, customer_id: str, session_id: str = None, 
                        limit: int = 20) -> List[Dict]:
        """Get chat history for customer or session"""
        try:
            if session_id:
                query = """
                SELECT TOP (?) log_id, session_id, user_message, bot_response,
                       intent_label, confidence_score, created_at
                FROM chatbot_chat_logs 
                WHERE session_id = ?
                ORDER BY created_at DESC
                """
                params = (limit, session_id)
            else:
                query = """
                SELECT TOP (?) log_id, session_id, user_message, bot_response,
                       intent_label, confidence_score, created_at
                FROM chatbot_chat_logs 
                WHERE customer_id = ?
                ORDER BY created_at DESC
                """
                params = (limit, customer_id)
            
            history = self.db.pool.execute_query(query, params)
            
            # Format timestamps
            for item in history:
                if item.get('created_at'):
                    item['created_at'] = item['created_at'].isoformat()
            
            return history or []
            
        except Exception as e:
            logger.error(f"Failed to get chat history: {str(e)}")
            return []
    
    def add_feedback(self, log_id: int, rating: int, comments: str = None) -> bool:
        """Add feedback for a chat interaction"""
        try:
            if not (1 <= rating <= 5):
                return False
            
            query = """
            INSERT INTO chatbot_feedback (log_id, rating, comments)
            VALUES (?, ?, ?)
            """
            
            self.db.pool.execute_query(query, (log_id, rating, comments), fetch=False)
            logger.info(f"Feedback added for log_id: {log_id}, rating: {rating}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add feedback: {str(e)}")
            return False
    
    def _create_error_response(self, session_id: str, message: str, error_type: str) -> Dict:
        """Create error response"""
        return {
            'session_id': session_id,
            'response': message,
            'intent': error_type,
            'confidence': 0.0,
            'entities': {},
            'suggestions': ["Try rephrasing your question", "Contact customer support"],
            'timestamp': datetime.now().isoformat()
        }
    
    def refresh_responses(self):
        """Refresh responses from database"""
        self._load_responses()
        return {"status": "success", "message": "Responses refreshed successfully"}