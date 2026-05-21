import os
from dotenv import load_dotenv

# Load .env file from the current directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    # X (Twitter) API Credentials
    API_KEY = os.getenv('X_API_KEY')
    API_KEY_SECRET = os.getenv('X_API_KEY_SECRET')
    ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')
    
    # Gemini API Credentials
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    
    # Promotional Smart Link (Redirect Target)
    APP_URL = os.getenv('APP_URL', 'https://onelink.to/renai_mode') # デフォルトの宣伝スマートリンク
    
    # Mode Settings
    PUBLISH_MODE = os.getenv('PUBLISH_MODE', 'dryrun').lower() # 'api' または 'dryrun'

    # Chatwork Settings
    CHATWORK_API_TOKEN = os.getenv('CHATWORK_API_TOKEN')
    CHATWORK_ROOM_ID = os.getenv('CHATWORK_ROOM_ID')

    @classmethod
    def validate(cls):
        missing = []
        for attr in ['API_KEY', 'API_KEY_SECRET', 'ACCESS_TOKEN', 'ACCESS_TOKEN_SECRET']:
            if not getattr(cls, attr):
                missing.append(f"X_{attr}")
        
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
            
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        return True
