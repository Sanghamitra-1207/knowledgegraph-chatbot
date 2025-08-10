# GraphRAG Expert Finder

A chatbot solution that acts as an "Experts Finder" tool, leveraging Graph Retrieval-Augmented Generation (GraphRAG) to identify subject matter experts within Roche organization. The system searches through existing data sources (Workday profiles, Knowledge Articles) to provide contextual information about employees with specific expertise.

## 🏗️ Architecture Overview

The solution combines:
- **Graph Database** (AWS Neptune Analytics) for storing entity relationships
- **Vector Store** (AWS OpenSearch Serverless) for semantic search
- **LLM Integration** (Claude 3.5 Sonnet) for natural language processing (Galileo)
- **Embedding Models** for semantic understanding (Galileo)

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- AWS Account with Neptune Graph and OpenSearch Serverless access
- API keys for Galileo (Roche's AI platform)

### Environment Setup

1. Clone the repository:
```bash
git clone https://code.roche.com/pdalm-data-engineering/graph-rag.git
cd graph-rag
```

2. Install in development mode:
```bash
make install-dev
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```bash
# DWS API Credentials
DWS_API_KEY=your_dws_api_key
DWS_API_ID=your_dws_api_id

# Galileo AI Platform
GALILEO_AWS_KEY=your_galileo_aws_key
GALILEO_AZURE_KEY=your_galileo_azure_key

# AWS Configuration
AWS_DEFAULT_REGION=eu-central-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_ENCRYPTION_KEY_ID=your_s3_encryption_key_id
```

## 📊 Data Pipeline

### Step 1: Extract Expert Data

Extract expert profiles, research outputs, and works from the DWS API:

```bash
# Export expert data from DWS API
make run-export
# or
python tools/export.py
```

This will:
- Fetch expert profiles from Workday/DWS
- Retrieve associated research outputs and works
- Combine experts with their works
- Optionally anonymize data for privacy
- Save individual expert files to `data/experts/`

**Output Structure:**
```
data/
├── experts.json              # Raw expert profiles
├── works.json               # Research outputs and works
├── experts_with_works.json  # Combined dataset
└── experts/                 # Individual expert files
    ├── {expert_id}_{name}.json
    └── ...
```

### Step 2: Build Knowledge Graph

Build the graph and vector embeddings:

```bash
# Build the knowledge graph
make run-build
# or
python tools/build_graph.py
```

This process:
1. **Extraction Phase**: Processes JSON files and extracts entities, relationships
2. **Graph Building**: Creates nodes and edges in Neptune (Neptune Analytics)
3. **Vector Indexing**: Generates embeddings and stores in OpenSearch Serverless

### Step 3: Query the Expert Finder

Use the retrieval system to find experts:

```python
from src.graph_rag.core.retrieve import create_retriever

# Initialize the retriever
retriever = create_retriever()

# Find experts by skill
response = retriever.query('Who has "Patient Outcomes" expertise?')
print(response)

# Find experts by domain
response = retriever.query('Who would be the best at Immunology research?')
print(response)

# Batch queries
queries = [
    'Who speaks German and has machine learning skills?',
    'What are the main research areas at Roche?',
    'Who has published papers on oncology?'
]
results = retriever.batch_query(queries)
```

or run below to execute sample queries
```bash
python src/graph_rag/core/retrieve.py
```

## 🛠️ Technology Stack

### Core Technologies
- **GraphRAG Toolkit**: AWS's lexical graph implementation
- **LlamaIndex**: Document processing and indexing
- **AWS Neptune Analytics**: Graph database for entity relationships
- **AWS OpenSearch Serverless**: Vector database for semantic search
- **Claude 3.5 Sonnet**: Large language model for query processing

## 📁 Project Structure

```
graph-rag/
├── src/graph_rag/          # Main package
│   └── core/
│       └── retrieve.py     # Query engine
├── tools/                  # Data processing tools
│   ├── export.py           # Data extraction from DWS
│   └── build_graph.py      # Graph construction
├── utilities/              # Helper functions
│   └── anonymize.py        # Data anonymization
├── notebooks/              # Jupyter notebooks
├── data/                   # Generated data (gitignored)
.env                        # Configuration file
```

## 🧪 Development

### Running Tests (TBD)
```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=src/

# Run specific test
pytest tests/test_retrieve.py -v
```

### Code Quality
```bash
# Format code
make format

# Lint code
make lint
```

### Development Workflow
```bash
# Firstly install the major dependency:
pip install https://github.com/awslabs/graphrag-toolkit/archive/refs/tags/v3.8.1.zip\#subdirectory\=lexical-graph

# Then install the rest of development dependencies
make install-dev

# Run export tool
make run-export

# Build graph
make run-build

# Run retrieval tests
python src/graph_rag/core/retrieve.py
```

## 🔧 Configuration

### Model Configuration
```python
# In QueryConfig dataclass
LLM_MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
EMBED_MODEL = "text-embedding-3-small-1"
MAX_TOKENS = 4096
EMBED_DIMENSIONS = 1024
```

### Store Configuration
```python
GRAPH_STORE_URL = "neptune-graph://your-neptune-graph"
VECTOR_STORE_URL = "aoss://https://your-opensearch-endpoint.com"
```

## 📈 Performance Considerations

- **Batch Processing**: Process multiple experts in parallel
- **Checkpointing**: Resume interrupted graph builds
- **Caching**: Vector embeddings are cached for reuse
- **Rate Limiting**: Built-in delays for API calls

## 🔒 Security & Privacy

- **Data Anonymization**: Optional anonymization of sensitive data
- **AWS IAM**: Proper access controls for cloud resources
- **Environment Variables**: Secure credential management
- **Encryption**: S3 encryption for data at rest

## 🚨 Troubleshooting

### Common Issues

1. **Environment Variables**: Ensure all required variables are set
2. **AWS Permissions**: Verify Neptune and OpenSearch access
3. **API Limits**: Check Galileo API rate limits
4. **Memory**: Large datasets may require increased memory allocation

### Logging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a merge request

## 📞 Support

For questions or issues:
- Create an issue in GitLab
- Contact the PDALM Data Engineering team
- Check the documentation in `docs/`

## 📋 License

Internal Roche project - see LICENSE file for details.

---

*This Expert Finder solution leverages cutting-edge GraphRAG technology to make organizational knowledge more discoverable and accessible.*