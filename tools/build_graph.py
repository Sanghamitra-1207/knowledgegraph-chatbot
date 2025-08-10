import os
import glob
import time
import logging
from pathlib import Path
from typing import List, Optional

from graphrag_toolkit.lexical_graph import LexicalGraphIndex, set_logging_config, IndexingConfig
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
from graphrag_toolkit.lexical_graph.indexing.load import S3BasedDocs
from graphrag_toolkit.lexical_graph.indexing.build import Checkpoint

from llama_index.core.readers.json import JSONReader
from llama_index.llms.openllm import OpenLLM
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from graphrag_toolkit.lexical_graph import GraphRAGConfig


class Config:
    """Configuration class for graph building."""
    
    GRAPH_STORE = "neptune-graph://g-76pgb4ql43"
    VECTOR_STORE = "aoss://https://r8mamuo7hin4k3xihz9a.eu-central-1.aoss.amazonaws.com"
    REGION = "eu-central-1"
    BUCKET_NAME = "grap-bucket"
    GALILEO_URL = "https://us.aigw.galileo.roche.com/v1"
    LLM_MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    EMBED_MODEL = "text-embedding-3-small-1"
    COLLECTION_ID = "20250623-154537"
    JSON_DIR = "experts"
    SLEEP_DURATION = 30
    MAX_TOKENS = 4096
    EMBED_DIMENSIONS = 1024
    
    @classmethod
    def validate_environment(cls) -> None:
        """Validate required environment variables."""
        required_vars = [
            "GALILEO_AWS_KEY",
            "GALILEO_AZURE_KEY", 
            "S3_ENCRYPTION_KEY_ID"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")


class GraphBuilder:
    """Main class for building graphs from JSON data."""
    
    def __init__(self, config: Config = None):
        """Initialize the GraphBuilder."""
        self.config = config or Config()
        self.config.validate_environment()
        
        self._setup_logging()
        self._setup_models()
        self._setup_stores()
        self._setup_graph_index()
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        set_logging_config('INFO')
        self.logger = logging.getLogger(__name__)
    
    def _setup_models(self) -> None:
        """Initialize LLM and embedding models."""
        self.llm = OpenLLM(
            model=self.config.LLM_MODEL,
            api_base=self.config.GALILEO_URL,
            is_chat_model=True,
            api_key=os.getenv("GALILEO_AWS_KEY"),
            max_tokens=self.config.MAX_TOKENS
        )
        
        self.embed_model = OpenAILikeEmbedding(
            model_name=self.config.EMBED_MODEL,
            api_base=self.config.GALILEO_URL,
            api_key=os.getenv("GALILEO_AZURE_KEY"),
            dimensions=self.config.EMBED_DIMENSIONS
        )
        
        # Configure GraphRAG
        GraphRAGConfig.extraction_llm = self.llm
        GraphRAGConfig.response_llm = self.llm
        GraphRAGConfig.embed_model = self.embed_model
    
    def _setup_stores(self) -> None:
        """Initialize graph and vector stores."""
        self.graph_store = GraphStoreFactory.for_graph_store(self.config.GRAPH_STORE)
        self.vector_store = VectorStoreFactory.for_vector_store(self.config.VECTOR_STORE)
    
    def _setup_graph_index(self) -> None:
        """Initialize the graph index."""
        self.graph_index = LexicalGraphIndex(
            self.graph_store,
            self.vector_store,
            indexing_config=IndexingConfig()
        )
    
    def _get_s3_docs(self, collection_id: Optional[str] = None) -> S3BasedDocs:
        """Create S3BasedDocs instance."""
        return S3BasedDocs(
            region=self.config.REGION,
            bucket_name=self.config.BUCKET_NAME,
            key_prefix='extracted',
            collection_id=collection_id,
            s3_encryption_key_id=os.getenv("S3_ENCRYPTION_KEY_ID")
        )
    
    def _load_json_documents(self, json_dir: str) -> List:
        """Load documents from JSON files."""
        json_path = Path(json_dir)
        if not json_path.exists():
            raise FileNotFoundError(f"Directory {json_dir} does not exist")
        
        json_files = list(json_path.glob("*.json"))
        if not json_files:
            raise ValueError(f"No JSON files found in {json_dir}")
        
        self.logger.info(f"Found {len(json_files)} JSON files")
        
        reader = JSONReader(
            levels_back=0,
            collapse_length=None,
            ensure_ascii=False,
            is_jsonl=False,
            clean_json=True
        )
        
        documents = []
        for json_file in json_files:
            try:
                docs = reader.load_data(input_file=str(json_file), extra_info={})
                documents.extend(docs)
                self.logger.info(f"Loaded {len(docs)} documents from {json_file.name}")
            except Exception as e:
                self.logger.error(f"Error loading {json_file}: {e}")
                raise
        
        return documents
    
    def extract_information(self, json_dir: str = None) -> None:
        """Extract information from JSON files."""
        json_dir = json_dir or self.config.JSON_DIR
        self.logger.info("Starting information extraction...")
        
        try:
            extracted_docs = self._get_s3_docs()
            checkpoint = Checkpoint('extraction-checkpoint')
            documents = self._load_json_documents(json_dir)
            
            self.logger.info(f"Processing {len(documents)} documents")
            
            for i, document in enumerate(documents, 1):
                self.logger.info(f"Processing document {i}/{len(documents)}")
                
                self.graph_index.extract(
                    [document], 
                    handler=extracted_docs,
                    checkpoint=checkpoint,
                    show_progress=True
                )
                
                if i < len(documents):  # Don't sleep after the last document
                    self.logger.info(f"Sleeping for {self.config.SLEEP_DURATION} seconds...")
                    time.sleep(self.config.SLEEP_DURATION)
            
            self.logger.info("Information extraction completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during extraction: {e}")
            raise
    
    def build_graph(self, collection_id: str = None) -> None:
        """Build the graph from extracted documents."""
        collection_id = collection_id or self.config.COLLECTION_ID
        self.logger.info(f"Starting graph build with collection_id: {collection_id}")
        
        try:
            extracted_docs = self._get_s3_docs(collection_id)
            checkpoint = Checkpoint('build-checkpoint')
            
            self.graph_index.build(
                extracted_docs,
                checkpoint=checkpoint,
                show_progress=True
            )
            
            self.logger.info("Graph build completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during graph build: {e}")
            raise


def build():
    """Main entry point."""
    try:
        builder = GraphBuilder()
        
        # Extract information
        builder.extract_information()
        
        # Build graph
        builder.build_graph()
        
    except Exception as e:
        logging.error(f"Building graph failed: {e}")
        raise


if __name__ == "__main__":
    build()