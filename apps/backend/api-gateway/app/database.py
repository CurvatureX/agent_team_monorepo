"""
Supabase Database Connection with RLS Support
"""

from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from app.config import settings
from app.utils import log_info, log_warning, log_error, log_debug

# Global admin Supabase client instance (service role)
admin_supabase: Optional[Client] = None

# Client cache for user tokens (to avoid recreating clients)
_user_clients: Dict[str, Client] = {}


def init_admin_supabase():
    """Initialize admin Supabase client with service role key"""
    global admin_supabase
    try:
        # Validate API key format
        if not settings.SUPABASE_SECRET_KEY:
            log_warning("SUPABASE_SECRET_KEY is empty")
            admin_supabase = None
            return
        # Create admin Supabase client
        admin_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
        if settings.DEBUG:
            log_info(f"🔧 Admin Supabase client initialized: {settings.SUPABASE_URL}")
    except Exception as e:
        error_msg = str(e)
        log_warning(f"Failed to connect to Supabase: {error_msg}")
        
        if "Legacy API keys are disabled" in error_msg:
            log_info("💡 Solution: Use new Secret key (sb_secret_...) from Supabase dashboard")
        elif "Invalid API key" in error_msg:
            log_info("💡 Check: Use Secret key (sb_secret_...) not Publishable key (sb_publishable_...)")
        else:
            log_info("💡 Check your .env file configuration")
            
        admin_supabase = None


def get_admin_supabase() -> Optional[Client]:
    """Get the admin Supabase client instance (service role)"""
    if admin_supabase is None:
        init_admin_supabase()
    return admin_supabase


def ensure_admin_supabase() -> Client:
    """Get admin Supabase client, ensure it's initialized"""
    client = get_admin_supabase()
    if client is None:
        raise RuntimeError(
            "Admin Supabase client not initialized. Check your SUPABASE_URL and SUPABASE_SECRET_KEY configuration."
        )
    return client


def get_user_supabase(access_token: str) -> Client:
    """
    Get Supabase client with user's access token for RLS
    
    Args:
        access_token: User's JWT access token from frontend
        
    Returns:
        Supabase client configured with user's token
    """
    # Check cache first
    if access_token in _user_clients:
        log_debug(f"🔐 Using cached Supabase client for token")
        return _user_clients[access_token]
    
    try:
        # Create user client with anon key and set user token
        if not settings.SUPABASE_ANON_KEY:
            # Fallback to service key if anon key not configured
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
        else:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        
        # Set the user's access token for RLS
        # For RLS, we need to set the Authorization header directly
        client.options.headers["Authorization"] = f"Bearer {access_token}"
        
        # Cache the client (but limit cache size to prevent memory leaks)
        if len(_user_clients) > 100:
            # Remove oldest entries
            _user_clients.clear()
            log_debug("🗑️ Cleared user client cache")
        
        _user_clients[access_token] = client
        log_debug(f"🔐 Created new Supabase client for user token")
        
        return client
        
    except Exception as e:
        log_error(f"🔥 Failed to create user Supabase client: {str(e)}")
        # Fallback to admin client
        return ensure_admin_supabase()


# Backwards compatibility
def init_supabase():
    """Initialize Supabase - backwards compatibility"""
    init_admin_supabase()


def get_supabase() -> Optional[Client]:
    """Get Supabase client - backwards compatibility"""
    return get_admin_supabase()


def ensure_supabase() -> Client:
    """Get Supabase client - backwards compatibility"""
    return ensure_admin_supabase()


# RLS-enabled Supabase Repository
class SupabaseRepository:
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    def _get_client(self, access_token: Optional[str] = None) -> Client:
        """
        Get appropriate Supabase client based on context
        
        Args:
            access_token: User's JWT access token for RLS operations
            
        Returns:
            Supabase client (user client if token provided, admin client otherwise)
        """
        if access_token:
            return get_user_supabase(access_token)
        else:
            return ensure_admin_supabase()
    
    def create(self, data: dict, access_token: Optional[str] = None):
        """
        Create a new record with RLS support
        
        Args:
            data: Record data to insert
            access_token: User's JWT token for RLS (if None, uses admin client)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).insert(data).execute()
            log_debug(f"✅ Created record in {self.table_name} (RLS: {'enabled' if access_token else 'admin'})")
            return result.data[0] if result.data else None
        except Exception as e:
            log_error(f"❌ Error creating record in {self.table_name}: {e}")
            return None
    
    def get_by_id(self, id: str, access_token: Optional[str] = None):
        """
        Get record by ID with RLS support
        
        Args:
            id: Record ID
            access_token: User's JWT token for RLS (if None, uses admin client)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).select("*").eq("id", id).execute()
            log_debug(f"🔍 Queried {self.table_name} by ID (RLS: {'enabled' if access_token else 'admin'})")
            return result.data[0] if result.data else None
        except Exception as e:
            log_error(f"❌ Error getting record from {self.table_name}: {e}")
            return None
    
    def get_by_session_id(self, session_id: str, access_token: Optional[str] = None):
        """
        Get records by session ID with RLS support
        
        Args:
            session_id: Session ID
            access_token: User's JWT token for RLS (if None, uses admin client)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).select("*").eq("session_id", session_id).execute()
            log_debug(f"🔍 Queried {self.table_name} by session_id (RLS: {'enabled' if access_token else 'admin'})")
            return result.data if result.data else []
        except Exception as e:
            log_error(f"❌ Error getting records from {self.table_name}: {e}")
            return []
    
    def get_by_user_id(self, user_id: str, access_token: Optional[str] = None):
        """
        Get records by user ID with RLS support
        
        Args:
            user_id: User ID
            access_token: User's JWT token for RLS (if None, uses admin client)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).select("*").eq("user_id", user_id).execute()
            log_debug(f"🔍 Queried {self.table_name} by user_id (RLS: {'enabled' if access_token else 'admin'})")
            return result.data if result.data else []
        except Exception as e:
            log_error(f"❌ Error getting user records from {self.table_name}: {e}")
            return []
    
    def update(self, id: str, data: dict, access_token: Optional[str] = None):
        """
        Update record with RLS support
        
        Args:
            id: Record ID
            data: Update data
            access_token: User's JWT token for RLS (if None, uses admin client)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).update(data).eq("id", id).execute()
            log_debug(f"✏️ Updated record in {self.table_name} (RLS: {'enabled' if access_token else 'admin'})")
            return result.data[0] if result.data else None
        except Exception as e:
            log_error(f"❌ Error updating record in {self.table_name}: {e}")
            return None
    
    def delete(self, id: str, access_token: Optional[str] = None):
        """
        Delete record with RLS support
        
        Args:
            id: Record ID
            access_token: User's JWT token for RLS (if None, uses admin client)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).delete().eq("id", id).execute()
            log_debug(f"🗑️ Deleted record from {self.table_name} (RLS: {'enabled' if access_token else 'admin'})")
            return True
        except Exception as e:
            log_error(f"❌ Error deleting record from {self.table_name}: {e}")
            return False


# Specialized repository for chats table with sequence number support
class ChatsRepository(SupabaseRepository):
    def __init__(self):
        super().__init__("chats")
    
    def get_next_sequence_number(self, session_id: str, access_token: Optional[str] = None) -> int:
        """
        Get the next sequence number for a session
        
        Args:
            session_id: Session ID
            access_token: User's JWT token for RLS
            
        Returns:
            Next sequence number (1 if no messages exist)
        """
        try:
            client = self._get_client(access_token)
            result = client.table(self.table_name).select("sequence_number").eq("session_id", session_id).order("sequence_number", desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]["sequence_number"] + 1
            else:
                return 1
        except Exception as e:
            log_error(f"❌ Error getting next sequence number: {e}")
            return 1
    
    def create(self, data: dict, access_token: Optional[str] = None):
        """
        Create a new chat message with automatic sequence number
        
        Args:
            data: Message data (must include session_id and user_id)
            access_token: User's JWT token for RLS
        """
        try:
            # Get next sequence number
            session_id = data.get("session_id")
            if not session_id:
                log_error("❌ session_id is required for chat messages")
                return None
            
            sequence_number = self.get_next_sequence_number(session_id, access_token)
            data["sequence_number"] = sequence_number
            
            # Ensure message_type is set (backward compatibility)
            if "type" in data and "message_type" not in data:
                data["message_type"] = data.pop("type")
            
            return super().create(data, access_token)
        except Exception as e:
            log_error(f"❌ Error creating chat message: {e}")
            return None


# Backwards compatibility - MVP Repository
class MVPSupabaseRepository(SupabaseRepository):
    """Backwards compatible MVP repository - delegates to new RLS repository"""
    
    def create(self, data: dict):
        """MVP version without RLS"""
        return super().create(data, access_token=None)
    
    def get_by_id(self, id: str):
        """MVP version without RLS"""
        return super().get_by_id(id, access_token=None)
    
    def get_by_session_id(self, session_id: str):
        """MVP version without RLS"""
        return super().get_by_session_id(session_id, access_token=None)
    
    def get_by_user_id(self, user_id: str):
        """MVP version without RLS"""
        return super().get_by_user_id(user_id, access_token=None)
    
    def update(self, id: str, data: dict):
        """MVP version without RLS"""
        return super().update(id, data, access_token=None)
    
    def delete(self, id: str):
        """MVP version without RLS"""
        return super().delete(id, access_token=None)


# RLS-enabled instances (recommended for new code)
sessions_rls_repo = SupabaseRepository("sessions")
chats_rls_repo = ChatsRepository()
