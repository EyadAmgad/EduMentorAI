"""
Custom storage backend for Supabase Storage
"""
import os
import mimetypes
from io import BytesIO
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.storage import Storage
from django.core.exceptions import SuspiciousOperation
from django.utils.deconstruct import deconstructible

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase package is required for SupabaseStorage")


@deconstructible
class SupabaseStorage(Storage):
    """
    Custom storage backend for Supabase Storage
    """
    
    def __init__(self, **kwargs):
        self.supabase_url = getattr(settings, 'SUPABASE_URL', '')
        self.supabase_key = getattr(settings, 'SUPABASE_KEY', '')
        self.bucket_name = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'documents')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in settings")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        super().__init__(**kwargs)
    
    def _save(self, name, content):
        """
        Save file to Supabase Storage
        """
        try:
            # Read content
            if hasattr(content, 'read'):
                file_content = content.read()
            else:
                file_content = content
            
            # Get MIME type
            content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
            
            # Upload to Supabase Storage
            response = self.client.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_content,
                file_options={'content-type': content_type}
            )
            
            if response.status_code == 200:
                return name
            else:
                raise Exception(f"Failed to upload file: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error uploading file to Supabase: {str(e)}")
    
    def _open(self, name, mode='rb'):
        """
        Download file from Supabase Storage
        """
        try:
            response = self.client.storage.from_(self.bucket_name).download(name)
            return BytesIO(response)
        except Exception as e:
            raise Exception(f"Error downloading file from Supabase: {str(e)}")
    
    def delete(self, name):
        """
        Delete file from Supabase Storage
        """
        try:
            response = self.client.storage.from_(self.bucket_name).remove([name])
            return response.status_code == 200
        except Exception as e:
            raise Exception(f"Error deleting file from Supabase: {str(e)}")
    
    def exists(self, name):
        """
        Check if file exists in Supabase Storage
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name),
                search=os.path.basename(name)
            )
            return len(response) > 0
        except Exception:
            return False
    
    def size(self, name):
        """
        Get file size from Supabase Storage
        """
        try:
            files = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name),
                search=os.path.basename(name)
            )
            if files:
                return files[0].get('metadata', {}).get('size', 0)
            return 0
        except Exception:
            return 0
    
    def url(self, name):
        """
        Get public URL for file
        """
        try:
            response = self.client.storage.from_(self.bucket_name).get_public_url(name)
            return response
        except Exception:
            return urljoin(
                self.supabase_url,
                f"/storage/v1/object/public/{self.bucket_name}/{name}"
            )
    
    def listdir(self, path):
        """
        List directory contents
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(path=path)
            directories = []
            files = []
            
            for item in response:
                if item.get('name'):
                    if '.' in item['name']:
                        files.append(item['name'])
                    else:
                        directories.append(item['name'])
            
            return directories, files
        except Exception:
            return [], []
    
    def get_accessed_time(self, name):
        """
        Get last accessed time (not supported by Supabase Storage)
        """
        raise NotImplementedError("Supabase Storage doesn't support accessed time")
    
    def get_created_time(self, name):
        """
        Get creation time
        """
        try:
            files = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name),
                search=os.path.basename(name)
            )
            if files:
                return files[0].get('created_at')
            return None
        except Exception:
            return None
    
    def get_modified_time(self, name):
        """
        Get modification time
        """
        try:
            files = self.client.storage.from_(self.bucket_name).list(
                path=os.path.dirname(name),
                search=os.path.basename(name)
            )
            if files:
                return files[0].get('updated_at')
            return None
        except Exception:
            return None
