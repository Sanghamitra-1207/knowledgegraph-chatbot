"""This script fetches data from the DWS API, processes it, and saves it to JSON files.
It retrieves outputs and works, then fetches expert profiles based on the outputs and works data.
It requires the DWS API key and ID to be set in the environment variables."""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
import dotenv
import sys
from pathlib import Path

# Add parent directory to path to import utilities
sys.path.append(str(Path(__file__).parent.parent))
from utilities import anonymize

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

dotenv.load_dotenv(override=True)

class Config:
    """Configuration class for API endpoints and settings."""
    
    SINEQUA_OUTPUTS_URL = "https://dws.roche.com/DigitalWorkspace_OCS_API/rest/Sinequa/OCS_Output"
    SINEQUA_WORKS_URL = "https://dws.roche.com/DigitalWorkspace_OCS_API/rest/Sinequa/OCS_Work"
    SINEQUA_EXPERT_PROFILE_URL = "https://dws.roche.com/DigitalWorkspace_Home_API/rest/Sinequa/GetExpertProfile_GET"

    DATA_DIR = Path("data")
    EXPERTS_DIR = DATA_DIR / "experts"

    DEFAULT_LIMIT = 10
    REQUEST_TIMEOUT = 30
    SHOULD_ANONYMIZE = True
    
    @classmethod
    def validate_environment(cls) -> None:
        """Validate required environment variables."""
        required_vars = ["DWS_API_KEY", "DWS_API_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")


class DWSAPIClient:
    """Client for interacting with the DWS API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-DWS-OCS-Key": os.getenv("DWS_API_KEY"),
            "X-DWS-OCS-AppId": os.getenv("DWS_API_ID"),
        })
    
    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a GET request to the API with error handling."""
        try:
            response = self.session.get(
                url, 
                params=params, 
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {url}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from {url}: {e}")
            raise
    
    def get_outputs_and_works(self, limit: int = None) -> List[Dict[str, Any]]:
        """Fetch outputs and works data from the DWS API."""
        limit = limit or self.config.DEFAULT_LIMIT
        params = {"Limit": limit}
        
        logger.info(f"Fetching outputs and works with limit: {limit}")
        
        outputs_data = self._make_request(self.config.SINEQUA_OUTPUTS_URL, params)
        works_data = self._make_request(self.config.SINEQUA_WORKS_URL, params)
        
        outputs_records = outputs_data.get("RecordList", [])
        works_records = works_data.get("RecordList", [])
        
        logger.info(f"Retrieved {len(outputs_records)} outputs and {len(works_records)} works")
        
        return works_records + outputs_records
    
    def get_expert_profile(self, expert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single expert profile by ID."""
        params = {"UserId": expert_id}
        
        try:
            response_data = self._make_request(self.config.SINEQUA_EXPERT_PROFILE_URL, params)
            records = response_data.get("RecordList", [])
            
            if records:
                return records[0]
            else:
                logger.warning(f"No expert profile found for ID: {expert_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch expert profile for ID {expert_id}: {e}")
            return None
    
    def get_experts(self, outputs_and_works: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch expert profiles based on outputs and works data."""
        # Extract unique expert IDs, filtering out None values
        expert_ids = {
            item.get("ExpertId") 
            for item in outputs_and_works 
            if item.get("ExpertId") is not None
        }
        
        logger.info(f"Found {len(expert_ids)} unique expert IDs")
        
        experts = []
        for expert_id in expert_ids:
            expert_profile = self.get_expert_profile(expert_id)
            if expert_profile:
                experts.append(expert_profile)
        
        logger.info(f"Successfully fetched {len(experts)} expert profiles")
        return experts


class DataProcessor:
    """Handles data processing and file operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def ensure_directories(self) -> None:
        """Create necessary directories."""
        self.config.DATA_DIR.mkdir(exist_ok=True)
        
        if self.config.EXPERTS_DIR.exists():
            shutil.rmtree(self.config.EXPERTS_DIR)
        self.config.EXPERTS_DIR.mkdir(parents=True)
    
    def save_json(self, data: Any, filepath: Path) -> None:
        """Save data to a JSON file."""
        try:
            with filepath.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save data to {filepath}: {e}")
            raise
    
    def load_json(self, filepath: Path) -> Any:
        """Load data from a JSON file."""
        try:
            with filepath.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data from {filepath}: {e}")
            raise
    
    def save_initial_data(self, outputs_and_works: List[Dict[str, Any]], experts: List[Dict[str, Any]]) -> None:
        """Save the initial fetched data to JSON files."""
        # Separate outputs and works
        outputs = [item for item in outputs_and_works if 'Output' in str(type(item)).title()]
        works = [item for item in outputs_and_works if 'Work' in str(type(item)).title()]
        
        # Save individual files
        self.save_json(outputs, self.config.DATA_DIR / "outputs.json")
        self.save_json(works, self.config.DATA_DIR / "works.json")
        self.save_json(outputs_and_works, self.config.DATA_DIR / "original_data.json")
        self.save_json(experts, self.config.DATA_DIR / "experts.json")
    
    def combine_experts_with_works(self, experts_file: str, works_file: str) -> List[Dict[str, Any]]:
        """Combine experts data with their associated works."""
        experts = self.load_json(self.config.DATA_DIR / experts_file)
        works = self.load_json(self.config.DATA_DIR / works_file)
        
        # Create a mapping of expert_id to works for efficient lookup
        works_by_expert = {}
        for work in works:
            expert_id = work.get("ExpertId")
            if expert_id:
                works_by_expert.setdefault(expert_id, []).append(work)
        
        # Add works to each expert
        for expert in experts:
            expert_id = expert.get("Id")
            expert["works"] = works_by_expert.get(expert_id, [])
        
        return experts
    
    def save_individual_expert_files(self, experts: List[Dict[str, Any]]) -> None:
        """Save each expert to a separate JSON file."""
        for expert in experts:
            expert_id = expert.get("Id", "unknown")
            expert_title = expert.get("Title", "").replace(" ", "_") or "untitled"
            
            filename = f"{expert_id}_{expert_title}.json"
            filepath = self.config.EXPERTS_DIR / filename
            
            self.save_json(expert, filepath)
        
        logger.info(f"Individual expert files saved to {self.config.EXPERTS_DIR}")
    
    def check_experts_without_works(self, experts: List[Dict[str, Any]]) -> None:
        """Log experts who have no associated works."""
        experts_without_works = [
            expert for expert in experts 
            if not expert.get("works")
        ]
        
        if experts_without_works:
            logger.warning(f"Found {len(experts_without_works)} experts without works:")
            for expert in experts_without_works:
                logger.warning(f"  - Expert ID: {expert.get('Id')}")
        else:
            logger.info("All experts have associated works")


class DWSDataExporter:
    """Main class that orchestrates the data export process."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.config.validate_environment()
        
        self.api_client = DWSAPIClient(self.config)
        self.data_processor = DataProcessor(self.config)
    
    def export_raw_data(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Export raw data from the DWS API."""
        logger.info("Starting raw data export...")
        
        # Fetch data from API
        outputs_and_works = self.api_client.get_outputs_and_works()
        experts = self.api_client.get_experts(outputs_and_works)
        
        # Save initial data
        self.data_processor.save_initial_data(outputs_and_works, experts)
        
        logger.info("Raw data export completed successfully")
        return outputs_and_works, experts
    
    def process_and_save_final_data(self) -> None:
        """Process the data and save final files."""
        logger.info("Processing final data...")
        
        # Determine which files to use based on anonymization setting
        if self.config.SHOULD_ANONYMIZE:
            logger.info("Anonymizing data...")
            anonymize.anonymize_data()
            experts_file = "experts_cleaned.json"
            works_file = "works_cleaned.json"
        else:
            experts_file = "experts.json"
            works_file = "works.json"
        
        # Combine experts with their works
        experts_with_works = self.data_processor.combine_experts_with_works(
            experts_file, works_file
        )
        
        # Save combined data
        self.data_processor.save_json(
            experts_with_works, 
            self.config.DATA_DIR / "experts_with_works.json"
        )
        
        # Save individual expert files
        self.data_processor.save_individual_expert_files(experts_with_works)
        
        # Check for experts without works
        self.data_processor.check_experts_without_works(experts_with_works)
        
        logger.info("Data processing completed successfully")
    
    def run(self) -> None:
        """Run the complete export process."""
        try:
            # Ensure directories exist
            self.data_processor.ensure_directories()
            
            # Export raw data
            self.export_raw_data()
            
            # Process and save final data
            self.process_and_save_final_data()
            
            logger.info("All operations completed successfully")
            
        except Exception as e:
            logger.error(f"Export process failed: {e}")
            raise


def main() -> None:
    """Main entry point."""
    try:
        exporter = DWSDataExporter()
        exporter.run()
    except Exception as e:
        logger.error(f"Exporter failed: {e}")
        raise


if __name__ == "__main__":
    main()