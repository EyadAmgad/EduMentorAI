"""
Supabase client utilities for EduMentorAI
"""
from django.conf import settings
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase package not available. Install with: pip install supabase")


class SupabaseClient:
    """
    Wrapper class for Supabase client with error handling
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.url = getattr(settings, 'SUPABASE_URL', '')
        self.key = getattr(settings, 'SUPABASE_KEY', '')
        self.service_role_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '')
        
        if SUPABASE_AVAILABLE and self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                self.client = None
        else:
            logger.warning("Supabase not configured or package not available")
    
    def is_available(self) -> bool:
        """Check if Supabase client is available"""
        return self.client is not None
    
    def create_user(self, email: str, password: str, **kwargs) -> Dict[str, Any]:
        """Create a new user via Supabase Auth"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.auth.sign_up({
                'email': email,
                'password': password,
                **kwargs
            })
            return response
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def sign_in_user(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in user via Supabase Auth"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            return response
        except Exception as e:
            logger.error(f"Error signing in user: {str(e)}")
            raise
    
    def sign_out_user(self) -> Dict[str, Any]:
        """Sign out current user"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.auth.sign_out()
            return response
        except Exception as e:
            logger.error(f"Error signing out user: {str(e)}")
            raise
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        """Get current user"""
        if not self.is_available():
            return None
        
        try:
            user = self.client.auth.get_user()
            return user
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def upload_file(self, bucket: str, path: str, file_content: bytes, 
                   content_type: str = 'application/octet-stream') -> Dict[str, Any]:
        """Upload file to Supabase Storage"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.storage.from_(bucket).upload(
                path=path,
                file=file_content,
                file_options={'content-type': content_type}
            )
            return response
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def download_file(self, bucket: str, path: str) -> bytes:
        """Download file from Supabase Storage"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.storage.from_(bucket).download(path)
            return response
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
    
    def delete_file(self, bucket: str, path: str) -> Dict[str, Any]:
        """Delete file from Supabase Storage"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.storage.from_(bucket).remove([path])
            return response
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """Get public URL for file"""
        if not self.is_available():
            return f"{self.url}/storage/v1/object/public/{bucket}/{path}"
        
        try:
            url = self.client.storage.from_(bucket).get_public_url(path)
            return url
        except Exception as e:
            logger.error(f"Error getting public URL: {str(e)}")
            return f"{self.url}/storage/v1/object/public/{bucket}/{path}"
    
    def create_bucket(self, bucket_name: str, public: bool = True) -> Dict[str, Any]:
        """Create a storage bucket"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            response = self.client.storage.create_bucket(bucket_name, public=public)
            return response
        except Exception as e:
            logger.error(f"Error creating bucket: {str(e)}")
            raise
    
    def execute_query(self, table: str, query_type: str = 'select', 
                     data: Dict[str, Any] = None, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute database query"""
        if not self.is_available():
            raise Exception("Supabase client not available")
        
        try:
            query = self.client.table(table)
            
            if query_type == 'select':
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                response = query.execute()
            elif query_type == 'insert':
                response = query.insert(data).execute()
            elif query_type == 'update':
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                response = query.update(data).execute()
            elif query_type == 'delete':
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                response = query.delete().execute()
            else:
                raise ValueError(f"Unsupported query type: {query_type}")
            
            return response
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise


# Global Supabase client instance
supabase_client = SupabaseClient()


def get_supabase_client() -> SupabaseClient:
    """Get the global Supabase client instance"""
    return supabase_client
