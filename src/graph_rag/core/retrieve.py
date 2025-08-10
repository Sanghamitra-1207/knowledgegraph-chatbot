"""Graph retrieval and query module for GraphRAG."""

import os
import logging
from typing import Optional, Dict
from dataclasses import dataclass

from graphrag_toolkit.lexical_graph import LexicalGraphQueryEngine, GraphRAGConfig
from graphrag_toolkit.lexical_graph.storage import GraphStoreFactory, VectorStoreFactory
from llama_index.llms.openllm import OpenLLM
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class QueryConfig:
    """Configuration for GraphRAG query engine."""
    
    # Model configurations
    LLM_MODEL: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    EMBED_MODEL: str = "text-embedding-3-small-1"
    API_BASE: str = "https://us.aigw.galileo.roche.com/v1"
    MAX_TOKENS: int = 4096
    EMBED_DIMENSIONS: int = 1024
    
    # Store configurations
    GRAPH_STORE_URL: str = "neptune-graph://g-76pgb4ql43"
    VECTOR_STORE_URL: str = "aoss://https://r8mamuo7hin4k3xihz9a.eu-central-1.aoss.amazonaws.com"
    
    @classmethod
    def validate_environment(cls) -> None:
        """Validate required environment variables."""
        required_vars = ["GALILEO_AWS_KEY", "GALILEO_AZURE_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")


class GraphRAGRetriever:
    """Main class for GraphRAG retrieval and querying."""
    
    def __init__(self, config: QueryConfig = None):
        """Initialize the GraphRAG retriever."""
        self.config = config or QueryConfig()
        self.config.validate_environment()
        
        self._setup_models()
        self._setup_stores()
        self._setup_query_engine()
    
    def _setup_models(self) -> None:
        """Initialize LLM and embedding models."""
        try:
            self.llm = OpenLLM(
                model=self.config.LLM_MODEL,
                api_base=self.config.API_BASE,
                is_chat_model=True,
                api_key=os.getenv("GALILEO_AWS_KEY"),
                max_tokens=self.config.MAX_TOKENS
            )
            
            self.embed_model = OpenAILikeEmbedding(
                model_name=self.config.EMBED_MODEL,
                api_base=self.config.API_BASE,
                api_key=os.getenv("GALILEO_AZURE_KEY"),
                dimensions=self.config.EMBED_DIMENSIONS
            )
            
            # Configure GraphRAG
            GraphRAGConfig.extraction_llm = self.llm
            GraphRAGConfig.response_llm = self.llm
            GraphRAGConfig.embed_model = self.embed_model
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    def _setup_stores(self) -> None:
        """Initialize graph and vector stores."""
        try:
            self.graph_store = GraphStoreFactory.for_graph_store(self.config.GRAPH_STORE_URL)
            self.vector_store = VectorStoreFactory.for_vector_store(self.config.VECTOR_STORE_URL)
            
        except Exception as e:
            logger.error(f"Failed to initialize stores: {e}")
            raise
    
    def _setup_query_engine(self) -> None:
        """Initialize the query engine."""
        try:
            self.query_engine = LexicalGraphQueryEngine.for_semantic_guided_search(
                self.graph_store, 
                self.vector_store
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize query engine: {e}")
            raise
    
    def query(self, question: str, **kwargs) -> Optional[str]:
        """Execute a query against the graph.
        
        Args:
            question: The question to ask
            **kwargs: Additional query parameters
            
        Returns:
            The response string or None if query failed
        """
        if not question.strip():
            logger.warning("Empty query provided")
            return None
        
        try:
            logger.info(f"Executing query: {question}")
            response = self.query_engine.query(question, **kwargs)
            
            if hasattr(response, 'response'):
                result = response.response
                logger.info("Query executed successfully")
                return result
            else:
                logger.warning("Query response has no 'response' attribute")
                return str(response)
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return None
    
    def batch_query(self, questions: list[str]) -> Dict[str, Optional[str]]:
        """Execute multiple queries.
        
        Args:
            questions: List of questions to ask
            
        Returns:
            Dictionary mapping questions to responses
        """
        results = {}
        
        for question in questions:
            logger.info(f"Processing question {len(results)+1}/{len(questions)}: {question}")
            results[question] = self.query(question)
        
        return results


def create_retriever(config: QueryConfig = None) -> GraphRAGRetriever:
    """Factory function to create a GraphRAG retriever."""
    return GraphRAGRetriever(config)


def main() -> None:
    """Main function for standalone execution of sample queries."""
    try:
        # Initialize retriever
        retriever = create_retriever()
        
        # Example queries
        queries = [
            'Who has "Patient Outcomes" skill?',
            'What skills are the most represented at Roche?'
        ]
        
        # Execute queries
        results = retriever.batch_query(queries)
        
        # Display results
        for question, answer in results.items():
            print(f"\n{'='*60}")
            print(f"Question: {question}")
            print(f"{'='*60}")
            if answer:
                print(f"Answer: {answer}")
            else:
                print("No answer received")
        
    except Exception as e:
        logger.error(f"GraphRAG retriever failed: {e}")
        raise


if __name__ == '__main__':
    main()