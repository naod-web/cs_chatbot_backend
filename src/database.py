import pyodbc
import threading
from contextlib import contextmanager
from queue import Queue
from typing import Optional, Any
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class DatabaseConnectionPool:
    """Connection pool for SQL Server (similar to HikariCP in Spring Boot)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        self.config = Config()
        self.pool = Queue(maxsize=self.config.DB_POOL_SIZE)
        self.active_connections = 0
        self._create_pool()
        logger.info(f"Database pool initialized with {self.config.DB_POOL_SIZE} connections")
    
    def _create_pool(self):
        """Create initial pool connections"""
        for _ in range(self.config.DB_MIN_IDLE):
            conn = self._create_connection()
            if conn:
                self.pool.put(conn)
                self.active_connections += 1
    
    def _create_connection(self) -> Optional[pyodbc.Connection]:
        """Create a new database connection"""
        try:
            conn = pyodbc.connect(self.config.DB_CONNECTION_STRING)
            conn.timeout = 30
            return conn
        except pyodbc.Error as e:
            logger.error(f"Failed to create database connection: {str(e)}")
            return None
    
    @contextmanager
    def get_connection(self):
        """Get a connection from pool (context manager)"""
        conn = None
        try:
            try:
                conn = self.pool.get(timeout=5)
            except:
                if self.active_connections < self.config.DB_POOL_SIZE:
                    conn = self._create_connection()
                    if conn:
                        self.active_connections += 1
            
            if not conn:
                raise Exception("No database connections available")
            
            yield conn
            
            # Return connection to pool
            self.pool.put(conn)
            
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
                self.active_connections -= 1
            raise
    
    @contextmanager
    def get_cursor(self):
        """Get a cursor from connection pool"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Any:
        """Execute a query with parameters"""
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch and query.strip().upper().startswith('SELECT'):
                    columns = [column[0] for column in cursor.description]
                    results = []
                    for row in cursor.fetchall():
                        results.append(dict(zip(columns, row)))
                    return results
                else:
                    return cursor.rowcount
                    
        except pyodbc.Error as e:
            logger.error(f"Database query error: {str(e)}")
            raise
    
    def close_all(self):
        """Close all connections in pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except:
                pass
        self.active_connections = 0
        logger.info("Database pool closed")


# Global database pool instance
db_pool = DatabaseConnectionPool()


class DatabaseManager:
    """Main database manager for chatbot operations"""
    
    def __init__(self):
        self.pool = db_pool
    
    def initialize_tables(self):
        """Initialize required tables if they don't exist"""
        try:
            # Check if we can connect to the existing Spring Boot tables
            self._check_spring_boot_tables()
            
            # Create chatbot-specific tables
            self._create_chatbot_tables()
            
            logger.info("Database tables initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize tables: {str(e)}")
            raise
    
    def _check_spring_boot_tables(self):
        """Check connection to existing Spring Boot database"""
        try:
            # Test connection by querying a common table
            query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            LIMIT 5
            """
            tables = self.pool.execute_query(query)
            logger.info(f"Connected to database. Found {len(tables)} tables")
            
            # Check for common Spring Boot tables
            common_tables = ['users', 'accounts', 'transactions', 'customers']
            for table in tables:
                if table['TABLE_NAME'].lower() in common_tables:
                    logger.info(f"Found Spring Boot table: {table['TABLE_NAME']}")
                    
        except Exception as e:
            logger.warning(f"Could not find Spring Boot tables: {str(e)}")
    
    def _create_chatbot_tables(self):
        """Create chatbot-specific tables"""
        
        # Create chatbot_responses table for pre-labeled responses
        responses_table = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chatbot_responses' AND xtype='U')
        CREATE TABLE chatbot_responses (
            response_id INT IDENTITY(1,1) PRIMARY KEY,
            intent_label NVARCHAR(100) NOT NULL,
            response_text NVARCHAR(2000) NOT NULL,
            keywords NVARCHAR(500),
            synonyms NVARCHAR(1000),
            category NVARCHAR(100),
            sub_category NVARCHAR(100),
            priority INT DEFAULT 1,
            is_active BIT DEFAULT 1,
            created_by NVARCHAR(100),
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE(),
            UNIQUE(intent_label)
        )
        """
        self.pool.execute_query(responses_table, fetch=False)
        
        # Create chatbot_chat_logs table
        chat_logs_table = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chatbot_chat_logs' AND xtype='U')
        CREATE TABLE chatbot_chat_logs (
            log_id INT IDENTITY(1,1) PRIMARY KEY,
            session_id NVARCHAR(100),
            customer_id NVARCHAR(100),
            user_message NVARCHAR(2000) NOT NULL,
            bot_response NVARCHAR(2000) NOT NULL,
            intent_label NVARCHAR(100),
            confidence_score DECIMAL(5,4),
            metadata NVARCHAR(MAX),
            created_at DATETIME DEFAULT GETDATE(),
            INDEX idx_customer_id (customer_id),
            INDEX idx_session_id (session_id),
            INDEX idx_created_at (created_at)
        )
        """
        self.pool.execute_query(chat_logs_table, fetch=False)
        
        # Create chatbot_feedback table
        feedback_table = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chatbot_feedback' AND xtype='U')
        CREATE TABLE chatbot_feedback (
            feedback_id INT IDENTITY(1,1) PRIMARY KEY,
            log_id INT,
            rating INT CHECK (rating BETWEEN 1 AND 5),
            comments NVARCHAR(500),
            created_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (log_id) REFERENCES chatbot_chat_logs(log_id) ON DELETE CASCADE
        )
        """
        self.pool.execute_query(feedback_table, fetch=False)
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX idx_responses_category ON chatbot_responses(category)",
            "CREATE INDEX idx_responses_active ON chatbot_responses(is_active)",
            "CREATE INDEX idx_logs_intent ON chatbot_chat_logs(intent_label)"
        ]
        
        for index in indexes:
            try:
                self.pool.execute_query(index, fetch=False)
            except:
                pass  # Index might already exist
    
    def seed_default_responses(self):
        """Seed default responses for common banking queries"""
        
        # Check if responses already exist
        count_query = "SELECT COUNT(*) as count FROM chatbot_responses"
        result = self.pool.execute_query(count_query)
        
        if result and result[0]['count'] == 0:
            default_responses = [
                # Greetings
                ("greeting", "Hello! Welcome to SiketBank. How can I assist you today?", "hello,hi,hey,greetings,good morning,good afternoon", "Greetings", 1),
                
                # Account Related
                ("account_balance", "You can check your account balance by:\n1. Logging into online banking\n2. Using our mobile app\n3. Visiting any ATM\n4. Calling customer service at 1-800-SIKET-BANK", "balance,account balance,check balance,how much money,current balance", "Account", 1),
                ("account_statement", "You can download your account statement:\n1. Online banking → Statements\n2. Mobile app → My Accounts\n3. Visit branch with ID\nStatements available for last 7 years.", "statement,account statement,bank statement,transaction history", "Account", 2),
                
                # Loan Related
                ("loan_inquiry", "For loan inquiries:\n• Personal Loans: 5-15% interest\n• Home Loans: 7-10% interest\n• Auto Loans: 6-12% interest\nApply online or visit any branch.", "loan,borrow,money,credit,finance,mortgage,personal loan,home loan,car loan", "Loans", 1),
                ("loan_application", "To apply for a loan:\n1. Visit our website → Loans section\n2. Fill online application\n3. Upload documents\n4. Get approval in 24-48 hours", "apply loan,loan application,how to get loan,loan process", "Loans", 2),
                
                # Branch & ATM
                ("branch_locations", "We have branches across the country:\n1. Use branch locator on website\n2. Download mobile app\n3. Call 1-800-SIKET-LOCATE\nMain branch: 123 Banking Street", "branch,location,near me,atm,where is,bank location,nearest branch", "Locations", 1),
                ("working_hours", "Our business hours:\n• Weekdays: 9:00 AM - 5:00 PM\n• Saturdays: 10:00 AM - 2:00 PM\n• Sundays: Closed\n• 24/7 Online Banking & ATMs", "hours,open,close,time,schedule,business hours,operating hours", "Hours", 2),
                
                # Customer Support
                ("customer_support", "Customer support options:\n• Phone: 1-800-SIKET-HELP (24/7)\n• Email: support@siketbank.com\n• Live Chat: Available on website\n• Branch: Visit during business hours", "help,support,contact,phone number,email,customer service,assistance", "Support", 1),
                
                # Transfers & Payments
                ("transfer_funds", "To transfer funds:\n1. Log into online banking\n2. Go to Transfers → New Transfer\n3. Select account and amount\n4. Confirm details\nDaily limit: $10,000", "transfer,money,send money,wire transfer,bank transfer,electronic transfer", "Transactions", 1),
                ("bill_payment", "Pay bills through:\n1. Online banking → Bill Pay\n2. Mobile app → Payments\n3. Auto-pay setup available\n4. Visit branch for cash payments", "bill,payment,pay bill,utility bill,credit card payment", "Transactions", 2),
                
                # Card Services
                ("card_issues", "For card issues:\n• Lost/Stolen: Call 1-800-SIKET-CARD immediately\n• Block card: Use mobile app\n• Replacement: 3-5 business days\n• Emergency cash: Available at branches", "card,debit card,credit card,lost card,stolen card,card blocked,new card", "Cards", 1),
                ("card_activation", "Activate your card:\n1. Call 1-800-SIKET-ACTIVATE\n2. Use mobile app → Card Services\n3. Visit ATM with PIN\n4. Online banking", "activate card,new card activation,card not working", "Cards", 2),
                
                # Internet Banking
                ("online_banking", "Online banking features:\n• View accounts & balances\n• Transfer funds\n• Pay bills\n• Download statements\n• Manage cards\nRegister at www.siketbank.com/online", "online banking,internet banking,mobile banking,digital banking", "Digital", 1),
                
                # Security
                ("security_concerns", "Security measures:\n• 2-factor authentication\n• SMS alerts for transactions\n• Biometric login\n• 24/7 fraud monitoring\nReport fraud: 1-800-SIKET-FRAUD", "security,hacked,fraud,suspicious,password reset", "Security", 1)
            ]
            
            insert_query = """
            INSERT INTO chatbot_responses 
            (intent_label, response_text, keywords, category, priority)
            VALUES (?, ?, ?, ?, ?)
            """
            
            for intent, response, keywords, category, priority in default_responses:
                self.pool.execute_query(
                    insert_query,
                    (intent, response, keywords, category, priority),
                    fetch=False
                )
            
            logger.info(f"Seeded {len(default_responses)} default responses")