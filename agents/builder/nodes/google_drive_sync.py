"""Google Drive integration node for the builder agent."""
import os
import logging
import asyncio
import time
import re
from typing import List, Optional, Set, Dict
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from pydantic import BaseModel, Field
from ..state import BuilderState, WorkflowStage, GoogleDriveConfig, GoogleDriveSyncInfo
from ..utils.logging_utils import log_state_change, log_error, log_validation
from ..utils.state_utils import save_state

# Set up logging
logger = logging.getLogger(__name__)

# Constants
EXPORTS_DIR = Path("exports")
PDF_PATTERN = r"FEN_([A-Z]{2,3})_(\d{3})\.pdf"  # Matches FEN_XXX_NNN.pdf
WATCH_TIMEOUT = 300  # 5 minutes timeout for watching exports

class DriveFileMetadata(BaseModel):
    """Metadata for a Drive file."""
    name: str
    mime_type: str
    parent_ids: List[str] = Field(default_factory=list)
    file_id: Optional[str] = None

class DriveUploadResult(BaseModel):
    """Result of a Drive file upload."""
    local_path: str
    drive_id: str
    name: str
    category: str = ""  # e.g., "ADP", "BAC", etc.
    sequence: int = 0   # e.g., 1, 2, 3 from 001, 002, 003

class DriveFolderStructure(BaseModel):
    """Structure of Drive folders."""
    root_id: str
    category_folders: Dict[str, str] = Field(default_factory=dict)

class DriveDocResult(BaseModel):
    """Result of a Drive document creation."""
    type: str
    drive_id: str
    title: str

class UploadedPDF(BaseModel):
    """Information about an uploaded PDF."""
    local_path: str
    drive_id: str

class CreatedDoc(BaseModel):
    """Information about a created Google Doc."""
    type: str
    drive_id: str

class GoogleDriveSyncInfo(BaseModel):
    """Information about the Google Drive sync process."""
    pdf_folder_id: str
    docs_folder_id: str
    uploaded_pdfs: List[UploadedPDF] = Field(default_factory=list)
    created_docs: List[CreatedDoc] = Field(default_factory=list)

class GoogleDriveConfig(BaseModel):
    """Configuration for Google Drive integration."""
    credentials_path: str
    folder_id: Optional[str] = None
    pdf_folder_name: str = "Insurance PDFs"
    docs_folder_name: str = "Generated Docs"

class DriveSync:
    """Google Drive sync handler."""
    
    def __init__(self, credentials_path: str):
        """Initialize the Drive sync handler."""
        self.credentials = self._load_credentials(credentials_path)
        self.service = build('drive', 'v3', credentials=self.credentials)
        logger.info("Successfully initialized Google Drive service")
    
    def _load_credentials(self, credentials_path: str) -> service_account.Credentials:
        """Load Google Drive credentials."""
        try:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
                
            return service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
        except Exception as e:
            logger.error(f"Failed to load credentials: {str(e)}")
            raise
    
    async def ensure_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Create or get folder ID."""
        try:
            # Search for existing folder
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            # Return existing folder ID if found
            if results.get('files'):
                folder_id = results['files'][0]['id']
                logger.info(f"Found existing folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            
            # Create new folder
            folder_metadata = DriveFileMetadata(
                name=folder_name,
                mime_type='application/vnd.google-apps.folder',
                parent_ids=[parent_id] if parent_id else []
            )
            
            folder = self.service.files().create(
                body=folder_metadata.model_dump(exclude_none=True),
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created new folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"Failed to ensure folder {folder_name}: {str(e)}")
            raise
    
    async def ensure_folder_structure(self, root_folder_name: str) -> DriveFolderStructure:
        """Create or get folder structure for PDFs."""
        try:
            # Create/get root folder
            root_id = await self.ensure_folder(root_folder_name)
            
            # Initialize folder structure
            structure = DriveFolderStructure(root_id=root_id)
            
            # Track unique categories we've seen
            categories = set()
            for pdf_file in EXPORTS_DIR.glob("FEN_*.pdf"):
                match = re.match(PDF_PATTERN, pdf_file.name)
                if match:
                    category = match.group(1)  # e.g., "ADP", "BAC"
                    categories.add(category)
            
            # Create category folders
            for category in sorted(categories):
                folder_name = f"FEN {category}"  # e.g., "FEN ADP", "FEN BAC"
                folder_id = await self.ensure_folder(folder_name, root_id)
                structure.category_folders[category] = folder_id
                logger.info(f"Ensured folder for category {category}: {folder_id}")
            
            return structure
            
        except Exception as e:
            logger.error(f"Failed to create folder structure: {str(e)}")
            raise
    
    async def upload_pdf(self, file_path: str, folder_id: str) -> DriveUploadResult:
        """Upload PDF file to Drive."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            file_name = Path(file_path).name
            match = re.match(PDF_PATTERN, file_name)
            category = match.group(1) if match else ""
            sequence = int(match.group(2)) if match else 0
            
            file_metadata = DriveFileMetadata(
                name=file_name,
                mime_type='application/pdf',
                parent_ids=[folder_id]
            )
            
            media = MediaFileUpload(
                file_path,
                mimetype='application/pdf',
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata.model_dump(exclude_none=True),
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Successfully uploaded PDF '{file_name}' with ID: {file_id}")
            
            return DriveUploadResult(
                local_path=file_path,
                drive_id=file_id,
                name=file_name,
                category=category,
                sequence=sequence
            )
            
        except Exception as e:
            logger.error(f"Failed to upload PDF {file_path}: {str(e)}")
            raise
    
    async def create_doc(self, title: str, content: str, folder_id: str) -> DriveDocResult:
        """Create a Google Doc."""
        try:
            doc_metadata = DriveFileMetadata(
                name=title,
                mime_type='application/vnd.google-apps.document',
                parent_ids=[folder_id]
            )
            
            doc = self.service.files().create(
                body=doc_metadata.model_dump(exclude_none=True),
                fields='id'
            ).execute()
            
            # Update document content
            doc_id = doc.get('id')
            self.service.files().update(
                fileId=doc_id,
                body={'content': content}
            ).execute()
            
            logger.info(f"Successfully created Google Doc '{title}' with ID: {doc_id}")
            
            return DriveDocResult(
                type="doc",
                drive_id=doc_id,
                title=title
            )
            
        except Exception as e:
            logger.error(f"Failed to create doc {title}: {str(e)}")
            raise

async def run_deck_export(deck_id: str) -> Optional[str]:
    """Run the deck export command and return the path to the exported PDF."""
    try:
        # Run the export command
        logger.info(f"Running deck export for {deck_id}")
        process = await asyncio.create_subprocess_shell(
            f"npm run deck export {deck_id}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Deck export failed with code {process.returncode}")
            logger.error(f"stderr: {stderr.decode()}")
            return None

        # The exported PDF should be in the deck's directory
        expected_pdf = Path(f"decks/{deck_id}/{deck_id}-slides-export.pdf")
        if not expected_pdf.exists():
            logger.error(f"Expected PDF not found at {expected_pdf}")
            return None

        logger.info(f"Successfully exported deck to {expected_pdf}")
        return str(expected_pdf)

    except Exception as e:
        logger.error(f"Error running deck export: {str(e)}")
        return None

async def watch_exports_directory(
    drive: DriveSync,
    folder_structure: DriveFolderStructure,
    processed_files: Set[str]
) -> List[DriveUploadResult]:
    """Watch exports directory for new PDFs and upload them."""
    uploaded_pdfs: List[DriveUploadResult] = []
    start_time = time.time()

    while time.time() - start_time < WATCH_TIMEOUT:
        # Check for new export files
        for pdf_file in EXPORTS_DIR.glob("FEN_*.pdf"):
            if str(pdf_file) not in processed_files:
                try:
                    match = re.match(PDF_PATTERN, pdf_file.name)
                    if not match:
                        logger.warning(f"File {pdf_file.name} doesn't match expected pattern")
                        continue
                        
                    category = match.group(1)
                    folder_id = folder_structure.category_folders.get(category)
                    if not folder_id:
                        logger.warning(f"No folder found for category {category}")
                        folder_id = folder_structure.root_id
                    
                    logger.info(f"Found new file: {pdf_file.name} (Category: {category})")
                    upload_result = await drive.upload_pdf(str(pdf_file), folder_id)
                    uploaded_pdfs.append(upload_result)
                    processed_files.add(str(pdf_file))
                    logger.info(f"Successfully uploaded to category folder: {pdf_file.name}")
                except Exception as e:
                    logger.error(f"Failed to upload {pdf_file.name}: {str(e)}")
        
        # Wait a bit before checking again
        await asyncio.sleep(2)
    
    return uploaded_pdfs

async def google_drive_sync(state: BuilderState) -> BuilderState:
    """Sync content with Google Drive."""
    try:
        # Verify we're in the correct stage
        if state.current_stage != WorkflowStage.GOOGLE_DRIVE_SYNC:
            logger.warning(f"Expected stage {WorkflowStage.GOOGLE_DRIVE_SYNC}, but got {state.current_stage}")
        
        # Check for required configuration
        if not state.google_drive_config:
            logger.error("No Google Drive configuration found in state")
            state.error_context = {
                "error": "Missing Google Drive configuration",
                "stage": "google_drive_sync"
            }
            return state
        
        # Initialize Drive sync
        try:
            drive = DriveSync(state.google_drive_config.credentials_path)
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive sync: {str(e)}")
            state.error_context = {
                "error": f"Drive initialization failed: {str(e)}",
                "stage": "google_drive_sync"
            }
            return state
        
        # Ensure folders exist
        try:
            folder_structure = await drive.ensure_folder_structure(state.google_drive_config.pdf_folder_name)
            logger.info(f"Created/verified folder structure with root: {folder_structure.root_id}")
        except Exception as e:
            logger.error(f"Failed to create folder structure: {str(e)}")
            state.error_context = {
                "error": f"Folder structure creation failed: {str(e)}",
                "stage": "google_drive_sync"
            }
            return state
        
        # Track processed files to avoid duplicates
        processed_files: Set[str] = set()
        
        # First, upload any existing exports
        logger.info("Checking for existing exports...")
        uploaded_pdfs: List[DriveUploadResult] = []
        
        for pdf_file in EXPORTS_DIR.glob("FEN_*.pdf"):
            try:
                match = re.match(PDF_PATTERN, pdf_file.name)
                if not match:
                    logger.warning(f"Skipping file that doesn't match pattern: {pdf_file.name}")
                    continue
                    
                category = match.group(1)
                folder_id = folder_structure.category_folders.get(category, folder_structure.root_id)
                
                upload_result = await drive.upload_pdf(str(pdf_file), folder_id)
                uploaded_pdfs.append(upload_result)
                processed_files.add(str(pdf_file))
                logger.info(f"Uploaded to category {category}: {pdf_file.name}")
            except Exception as e:
                logger.error(f"Failed to upload {pdf_file.name}: {str(e)}")
        
        # Watch for new exports
        logger.info("Watching for new exports...")
        new_uploads = await watch_exports_directory(drive, folder_structure, processed_files)
        uploaded_pdfs.extend(new_uploads)
        
        # Create Google Docs for slides and script
        docs: List[DriveDocResult] = []
        if state.slides:
            try:
                slides_doc = await drive.create_doc(
                    f"{state.metadata.title} - Slides",
                    state.slides,
                    folder_structure.root_id
                )
                docs.append(slides_doc)
            except Exception as e:
                logger.error(f"Failed to create slides doc: {str(e)}")
        
        if state.script:
            try:
                script_doc = await drive.create_doc(
                    f"{state.metadata.title} - Script",
                    state.script,
                    folder_structure.root_id
                )
                docs.append(script_doc)
            except Exception as e:
                logger.error(f"Failed to create script doc: {str(e)}")
        
        # Update state with Drive information
        state.drive_sync_info = GoogleDriveSyncInfo(
            pdf_folder_id=folder_structure.root_id,
            docs_folder_id=folder_structure.root_id,
            uploaded_pdfs=[
                UploadedPDF(
                    local_path=pdf.local_path,
                    drive_id=pdf.drive_id
                ) for pdf in uploaded_pdfs
            ],
            created_docs=[
                CreatedDoc(
                    type=doc.type,
                    drive_id=doc.drive_id
                ) for doc in docs
            ]
        )
        
        # Log completion and update stage
        log_state_change(
            state=state,
            node_name="google_drive_sync",
            change_type="complete",
            details={
                "pdfs_uploaded": len(uploaded_pdfs),
                "docs_created": len(docs),
                "pdf_folder_id": folder_structure.root_id,
                "docs_folder_id": folder_structure.root_id
            }
        )
        
        # Update workflow stage
        state.current_stage = WorkflowStage.GOOGLE_DRIVE_SYNC
        logger.info(f"Current stage updated to: {state.current_stage}")
        
        # Save state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
            logger.info(f"Saved state for deck {state.metadata.deck_id}")
        
        return state
        
    except Exception as e:
        log_error(state, "google_drive_sync", e)
        state.error_context = {
            "error": str(e),
            "stage": "google_drive_sync"
        }
        # Save error state
        if state.metadata and state.metadata.deck_id:
            save_state(state, state.metadata.deck_id)
        return state 