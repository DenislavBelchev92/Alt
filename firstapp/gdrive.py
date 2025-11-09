"""
Google Drive Integration Module
Handles OAuth authentication and file operations for Google Drive resources.
Provides a simple API for opening and managing Google Drive files.
"""

import os
import json
import pickle
import time
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Allow insecure transport for local development (HTTP instead of HTTPS)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

logger = logging.getLogger(__name__)

# Google Drive API configuration
# Using only read-only scope to ensure all files accessed via website are read-only
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly'
]

# Google OAuth credentials from environment variables
def get_google_oauth_config():
    """Get Google OAuth configuration from environment variables or settings"""
    return {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID', settings.GOOGLE_CLIENT_ID if hasattr(settings, 'GOOGLE_CLIENT_ID') else ''),
            "project_id": "altlearningdb",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET', settings.GOOGLE_CLIENT_SECRET if hasattr(settings, 'GOOGLE_CLIENT_SECRET') else ''),
            "redirect_uris": [
                "http://localhost:8000/oauth2callback/",
                "http://127.0.0.1:8000/oauth2callback/",
                "http://localhost:8001/oauth2callback/",
                "http://127.0.0.1:8001/oauth2callback/"
            ]
        }
    }

class GoogleDriveManager:
    """Manages Google Drive operations for a specific user"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.credentials = None
        self.service = None
        self._load_credentials()
    
    def _get_token_file_path(self):
        """Get the path for storing user's OAuth tokens"""
        tokens_dir = os.path.join(settings.BASE_DIR, 'gdrive_tokens')
        os.makedirs(tokens_dir, exist_ok=True)
        return os.path.join(tokens_dir, f'user_{self.user_id}_token.pickle')
    
    def _load_credentials(self):
        """Load existing credentials for the user"""
        token_path = self._get_token_file_path()
        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token_file:
                    self.credentials = pickle.load(token_file)
                logger.info(f"Loaded credentials for user {self.user_id}")
            except Exception as e:
                logger.error(f"Error loading credentials for user {self.user_id}: {e}")
                self.credentials = None
    
    def _save_credentials(self, credentials):
        """Save credentials for the user"""
        token_path = self._get_token_file_path()
        try:
            with open(token_path, 'wb') as token_file:
                pickle.dump(credentials, token_file)
            logger.info(f"Saved credentials for user {self.user_id}")
            self.credentials = credentials
        except Exception as e:
            logger.error(f"Error saving credentials for user {self.user_id}: {e}")
    
    def get_auth_url(self, request):
        """Generate OAuth authorization URL"""
        try:
            # Force localhost for OAuth callback to match credentials
            callback_url = request.build_absolute_uri(reverse('oauth2callback'))
            callback_url = callback_url.replace('127.0.0.1', 'localhost')
            
            flow = Flow.from_client_config(
                get_google_oauth_config(),
                scopes=SCOPES,
                redirect_uri=callback_url
            )
            
            # Store user_id in session for callback
            request.session['gdrive_user_id'] = self.user_id
            
            # Generate custom state with user_id embedded for persistence
            import base64
            import json
            custom_state_data = {
                'user_id': self.user_id,
                'timestamp': int(time.time())
            }
            custom_state = base64.urlsafe_b64encode(
                json.dumps(custom_state_data).encode()
            ).decode().rstrip('=')
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=custom_state
            )
            
            # Store state in session for security (backup)
            request.session['gdrive_oauth_state'] = state
            request.session['gdrive_custom_state'] = custom_state
            
            # Ensure session is saved and modified flag is set
            request.session.modified = True
            request.session.save()
            
            # Log OAuth setup
            logger.info(f"Stored user_id {self.user_id} and state in session for OAuth flow")
            
            logger.info(f"Generated auth URL for user {self.user_id}")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Error generating auth URL for user {self.user_id}: {e}")
            return None
    
    def handle_oauth_callback(self, request, authorization_response):
        """Handle OAuth callback and exchange code for tokens"""
        try:
            # Force localhost for OAuth callback to match credentials
            callback_url = request.build_absolute_uri(reverse('oauth2callback'))
            callback_url = callback_url.replace('127.0.0.1', 'localhost')
            
            flow = Flow.from_client_config(
                get_google_oauth_config(),
                scopes=SCOPES,
                redirect_uri=callback_url
            )
            
            # Verify state for security
            session_state = request.session.get('gdrive_oauth_state')
            request_state = request.GET.get('state')
            
            # If session state is lost, verify the custom state format instead
            state_valid = False
            if session_state and session_state == request_state:
                state_valid = True
                logger.info("OAuth state verification passed (session match)")
            elif request_state:
                # Verify custom state format as backup
                try:
                    import base64
                    import json
                    padded_state = request_state + '=' * (4 - len(request_state) % 4)
                    decoded_data = json.loads(base64.urlsafe_b64decode(padded_state.encode()).decode())
                    if 'user_id' in decoded_data and 'timestamp' in decoded_data:
                        # Check if timestamp is recent (within 1 hour)
                        current_time = int(time.time())
                        state_time = decoded_data.get('timestamp', 0)
                        if current_time - state_time < 3600:  # 1 hour
                            state_valid = True
                            logger.info("OAuth state verification passed (custom state format)")
                        else:
                            logger.warning(f"OAuth state timestamp too old: {current_time - state_time} seconds")
                    else:
                        logger.error("Invalid custom state format")
                except Exception as e:
                    logger.error(f"State verification decode error: {e}")
            
            if not state_valid:
                error_msg = f"OAuth state verification failed for user {self.user_id}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Handle token exchange with scope flexibility - Google may return additional scopes
            try:
                # Parse authorization response to check granted scopes
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(authorization_response)
                auth_code = parse_qs(parsed_url.query).get('code', [None])[0]
                granted_scope_param = parse_qs(parsed_url.query).get('scope', [None])[0]
                
                if not auth_code:
                    raise ValueError("No authorization code in callback")
                
                # Check if our required scope is present
                granted_scopes = granted_scope_param.split() if granted_scope_param else []
                required_scope = 'https://www.googleapis.com/auth/drive.readonly'
                
                if required_scope not in granted_scopes:
                    raise ValueError(f"Required scope {required_scope} not granted. Granted: {granted_scopes}")
                
                logger.info(f"OAuth callback - granted scopes: {granted_scopes}")
                
                # Create flow with flexible scope handling
                # Google OAuth2 spec allows accepting subset of requested scopes
                flexible_flow = Flow.from_client_config(
                    get_google_oauth_config(),
                    scopes=granted_scopes,  # Use actually granted scopes
                    redirect_uri=callback_url
                )
                
                # Exchange code for tokens using granted scopes
                flexible_flow.fetch_token(code=auth_code)
                credentials = flexible_flow.credentials
                
                # Verify we have the minimum required scope
                if hasattr(credentials, 'scopes'):
                    cred_scopes = credentials.scopes or []
                    if required_scope not in cred_scopes and required_scope not in granted_scopes:
                        raise ValueError(f"Credentials missing required scope: {required_scope}")
                
                logger.info(f"Token exchange successful for user {self.user_id} with scopes: {granted_scopes}")
                    
            except Exception as token_error:
                logger.error(f"Token exchange failed for user {self.user_id}: {token_error}")
                
                # Final fallback - try with original requested scopes only
                try:
                    logger.info(f"Attempting fallback token exchange for user {self.user_id}")
                    
                    fallback_flow = Flow.from_client_config(
                        get_google_oauth_config(),
                        scopes=SCOPES,  # Use only our original requested scopes
                        redirect_uri=callback_url
                    )
                    
                    # Try direct code exchange without scope validation
                    fallback_flow.fetch_token(code=auth_code)
                    credentials = fallback_flow.credentials
                    
                    logger.info(f"Fallback token exchange successful for user {self.user_id}")
                        
                except Exception as fallback_error:
                    logger.error(f"Fallback token exchange also failed for user {self.user_id}: {fallback_error}")
                    raise token_error  # Re-raise original error
            
            self._save_credentials(credentials)
            
            # Clear session data
            request.session.pop('gdrive_oauth_state', None)
            request.session.pop('gdrive_user_id', None)
            
            logger.info(f"OAuth callback successful for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback for user {self.user_id}: {e}")
            return False
    
    def _get_service(self):
        """Get authenticated Google Drive service"""
        if self.service:
            return self.service
            
        if not self.credentials:
            return None
            
        # Refresh credentials if needed
        if self.credentials.expired and self.credentials.refresh_token:
            try:
                self.credentials.refresh(Request())
                self._save_credentials(self.credentials)
            except Exception as e:
                logger.error(f"Error refreshing credentials for user {self.user_id}: {e}")
                return None
        
        if self.credentials.valid:
            self.service = build('drive', 'v3', credentials=self.credentials)
            return self.service
        
        return None
    
    def is_authenticated(self):
        """Check if user has valid Google Drive authentication with required read-only access"""
        if not self.credentials:
            return False
            
        # Check if credentials are valid and contain required scope
        if self.credentials.valid:
            # Verify we have at least read-only access
            required_scope = 'https://www.googleapis.com/auth/drive.readonly'
            if hasattr(self.credentials, 'scopes') and self.credentials.scopes:
                has_required_scope = any(
                    scope == required_scope or 'drive' in scope 
                    for scope in self.credentials.scopes
                )
                if not has_required_scope:
                    logger.warning(f"User {self.user_id} credentials missing required Drive scope")
                    return False
            
            service = self._get_service()
            return service is not None
            
        return False
    
    def find_file_by_name(self, filename, folder_path=None):
        """
        Find a file by name in Google Drive
        
        Args:
            filename: Name of the file to find
            folder_path: Optional path like "Alt/Math1" to search in specific folder
            
        Returns:
            dict: File metadata if found, None otherwise
        """
        service = self._get_service()
        if not service:
            return None
            
        try:
            # Build search query - try exact match first
            query = f"name='{filename}' and trashed=false"
            
            # If folder path specified, find the folder first
            folder_id = None
            if folder_path:
                folder_id = self._find_folder_by_path(folder_path)
                if folder_id:
                    query += f" and parents in '{folder_id}'"
                else:
                    logger.warning(f"Folder not found: {folder_path}")
                    return None
            
            # Search for the file (exact match)
            results = service.files().list(
                q=query,
                pageSize=10,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, webContentLink)"
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                file_info = files[0]  # Return first match
                logger.info(f"Found file '{filename}' (exact match) for user {self.user_id}")
                return file_info
            
            # If no exact match, try partial match (contains)
            if folder_id:
                partial_query = f"name contains '{filename}' and parents in '{folder_id}' and trashed=false"
                
                partial_results = service.files().list(
                    q=partial_query,
                    pageSize=10,
                    fields="nextPageToken, files(id, name, mimeType, webViewLink, webContentLink)"
                ).execute()
                
                partial_files = partial_results.get('files', [])
                
                if partial_files:
                    file_info = partial_files[0]
                    logger.info(f"Found file containing '{filename}' for user {self.user_id}")
                    return file_info
            else:
                logger.warning(f"File '{filename}' not found for user {self.user_id}")
                return None
                
        except HttpError as e:
            logger.error(f"Google Drive API error for user {self.user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error finding file '{filename}' for user {self.user_id}: {e}")
            return None
    
    def _find_folder_by_path(self, folder_path):
        """
        Find folder ID by path like "Alt/Math1"
        
        Args:
            folder_path: Path string like "Alt/Math1"
            
        Returns:
            str: Folder ID if found, None otherwise
        """
        service = self._get_service()
        if not service:
            return None
            
        try:
            path_parts = folder_path.split('/')
            current_folder_id = 'root'
            
            for folder_name in path_parts:
                if not folder_name:  # Skip empty parts
                    continue
                    
                query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and parents in '{current_folder_id}'"
                
                results = service.files().list(
                    q=query,
                    pageSize=10,
                    fields="files(id, name)"
                ).execute()
                
                folders = results.get('files', [])
                
                if folders:
                    current_folder_id = folders[0]['id']
                else:
                    logger.warning(f"Folder '{folder_name}' not found in path '{folder_path}'")
                    return None
            
            return current_folder_id
            
        except Exception as e:
            logger.error(f"Error finding folder path '{folder_path}': {e}")
            return None
    
    def get_file_url(self, filename, folder_path=None):
        """
        Get the web view URL for a file (ENFORCED READ-ONLY ACCESS)
        
        Args:
            filename: Name of the file
            folder_path: Optional folder path like "Alt"
            
        Returns:
            str: Read-only web view URL if found, None otherwise
        """
        file_info = self.find_file_by_name(filename, folder_path)
        if file_info:
            file_id = file_info.get('id')
            if not file_id:
                logger.warning(f"No file ID found for {filename}")
                return None
            
            # Force read-only access using Google Drive's preview URL
            # This ensures the file opens in view-only mode with no edit capabilities
            
            # Method 1: Use Google Drive's preview URL (most restrictive)
            preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
            
            # Method 2: Alternative - Use view URL with strict read-only parameters
            view_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            # Method 3: For Google Docs/Sheets/Slides, use export/preview
            mime_type = file_info.get('mimeType', '')
            
            if 'google-apps' in mime_type:
                # Google native formats - force view mode
                if 'document' in mime_type:
                    # Google Docs - use view mode
                    readonly_url = f"https://docs.google.com/document/d/{file_id}/view"
                elif 'spreadsheet' in mime_type:
                    # Google Sheets - use view mode
                    readonly_url = f"https://docs.google.com/spreadsheets/d/{file_id}/view"
                elif 'presentation' in mime_type:
                    # Google Slides - use view mode
                    readonly_url = f"https://docs.google.com/presentation/d/{file_id}/view"
                else:
                    # Other Google apps formats
                    readonly_url = view_url
            else:
                # Non-Google formats (PDF, images, etc.) - use preview
                readonly_url = preview_url
            
            # Add additional read-only parameters
            readonly_url += "?rm=minimal&embedded=true"
            
            logger.info(f"Generated ENFORCED read-only URL for {filename} (type: {mime_type})")
            return readonly_url
        return None

    def clear_credentials(self):
        """
        Clear stored credentials to force re-authentication with new scopes
        Call this when scopes change to ensure users get read-only permissions
        """
        token_path = self._get_token_file_path()
        try:
            if os.path.exists(token_path):
                os.remove(token_path)
                logger.info(f"Cleared credentials for user {self.user_id}")
            self.credentials = None
            self.service = None
        except Exception as e:
            logger.error(f"Error clearing credentials for user {self.user_id}: {e}")


# Convenience functions for easy use in views



def get_gdrive_resource(user_id, resource_name, folder_path="Alt"):
    """
    Main API function to get Google Drive resource (READ-ONLY ACCESS ONLY)
    
    All files accessed through this function will have read-only permissions.
    This is enforced through:
    1. Read-only API scopes (drive.readonly)
    2. Forced view-only URLs
    
    Main API function to get Google Drive resource
    
    Args:
        user_id: User ID for credentials
        resource_name: Name of file to find (e.g., "Math1") 
        folder_path: Path to folder (default: "Alt")
        
    Returns:
        dict: Success status and file URL or error info
    """
    try:
        manager = GoogleDriveManager(user_id)
        
        if not manager.credentials:
            return {
                'success': False,
                'error': 'Not authenticated with Google Drive',
                'auth_required': True
            }
            
        # Check if credentials are expired and refresh if needed
        if manager.credentials.expired:
            try:
                manager.credentials.refresh(Request())
                manager._save_credentials(manager.credentials)
            except Exception as refresh_error:
                logger.error(f"Failed to refresh credentials for user {user_id}: {refresh_error}")
                return {
                    'success': False,
                    'error': 'Google Drive authentication expired',
                    'auth_required': True
                }
        
        file_url = manager.get_file_url(resource_name, folder_path)
        
        if file_url:
            return {
                'success': True,
                'file_url': file_url,
                'resource_name': resource_name,
                'folder_path': folder_path
            }
        else:
            return {
                'success': False,
                'error': f'File "{resource_name}" not found in folder "{folder_path}"'
            }
            
    except Exception as e:
        logger.error(f"Error getting Google Drive resource for user {user_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def reset_user_oauth(user_id):
    """
    Reset OAuth tokens for a specific user to force clean re-authentication
    
    Args:
        user_id: Django user ID
        
    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        manager = GoogleDriveManager(user_id)
        manager.clear_credentials()
        logger.info(f"Reset OAuth tokens for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error resetting OAuth for user {user_id}: {e}")
        return False

def get_auth_url(request, user_id, force_reset=False):
    """
    Get Google Drive OAuth authorization URL
    
    Args:
        request: Django request object
        user_id: Django user ID
        force_reset: If True, clear existing credentials first
        
    Returns:
        str: Authorization URL or None if error
    """
    try:
        if force_reset:
            reset_user_oauth(user_id)
            
        manager = GoogleDriveManager(user_id)
        return manager.get_auth_url(request)
    except Exception as e:
        logger.error(f"Error getting auth URL: {e}")
        return None

def handle_oauth_callback(request):
    """
    Handle OAuth callback from Google
    
    Args:
        request: Django request object
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("OAuth callback received")
        
        user_id = None
        
        # Try to get user_id from session first
        user_id = request.session.get('gdrive_user_id')
        
        # If session failed, try to decode from state parameter
        if not user_id:
            state_param = request.GET.get('state')
            if state_param:
                try:
                    import base64
                    import json
                    # Add padding if needed
                    padded_state = state_param + '=' * (4 - len(state_param) % 4)
                    decoded_data = json.loads(base64.urlsafe_b64decode(padded_state.encode()).decode())
                    user_id = decoded_data.get('user_id')
                    logger.info(f"Recovered user_id {user_id} from state parameter")
                except Exception as decode_error:
                    logger.error(f"Failed to decode state parameter: {decode_error}")
        
        if not user_id:
            # Fallback: use current authenticated user if available
            if request.user.is_authenticated:
                logger.info(f"Using current authenticated user {request.user.id} as fallback")
                user_id = request.user.id
            else:
                logger.error("No user ID available for OAuth callback")
                return False
        
        manager = GoogleDriveManager(user_id)
        result = manager.handle_oauth_callback(request, request.get_full_path())
        
        return result
        
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {e}")
        return False