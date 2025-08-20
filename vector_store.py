"""
Vector Database Service for Past Proposals and RFP Responses
Integrates with LangChain and PostgreSQL vector storage
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
# Import with fallback for minimal requirements
try:
    from langchain_postgres import PGVector
    from langchain_openai import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document as LangChainDocument
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning("LangChain packages not available - using fallback vector store")
import uuid

logger = logging.getLogger(__name__)

class TenderVectorStore:
    """
    Vector database service for storing and retrieving past tender proposals
    """
    
    def __init__(self, database_url: str, collection_name: str = "tender_proposals"):
        self.database_url = database_url
        self.collection_name = collection_name
        self.embeddings = self._get_embeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.vector_store = None
        self._initialize_vector_store()
    
    def _get_embeddings(self):
        """Initialize embeddings - prefer OpenAI, fallback disabled for minimal build"""
        try:
            if LANGCHAIN_AVAILABLE and os.getenv('OPENAI_API_KEY'):
                logger.info("Using OpenAI embeddings")
                return OpenAIEmbeddings(
                    model="text-embedding-ada-002",
                    openai_api_key=os.getenv('OPENAI_API_KEY')
                )
            else:
                logger.warning("OpenAI API key not found or LangChain not available")
                return None
        except Exception as e:
            logger.error(f"Error initializing embeddings: {e}")
            return None
    
    def _initialize_vector_store(self):
        """Initialize the PGVector store"""
        try:
            if not LANGCHAIN_AVAILABLE or self.embeddings is None:
                logger.warning("Cannot initialize vector store - missing dependencies or embeddings")
                self.vector_store = None
                return
                
            self.vector_store = PGVector(
                collection_name=self.collection_name,
                connection_string=self.database_url,
                embeddings=self.embeddings,
            )
            logger.info(f"Vector store initialized with collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store = None
    
    def add_proposal_document(self, 
                            content: str, 
                            metadata: Dict[str, Any],
                            document_type: str = "proposal") -> bool:
        """
        Add a past proposal or RFP response to the vector store
        
        Args:
            content: Text content of the document
            metadata: Document metadata (title, client, year, etc.)
            document_type: Type of document (proposal, rfp_response, technical, commercial)
        
        Returns:
            bool: Success status
        """
        try:
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return False
            
            # Split document into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Create documents with metadata
            documents = []
            for i, chunk in enumerate(chunks):
                doc_metadata = {
                    **metadata,
                    "document_type": document_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "added_at": datetime.now().isoformat(),
                    "chunk_id": str(uuid.uuid4())
                }
                
                documents.append(LangChainDocument(
                    page_content=chunk,
                    metadata=doc_metadata
                ))
            
            # Add to vector store
            self.vector_store.add_documents(documents)
            
            logger.info(f"Added {len(documents)} chunks for document: {metadata.get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding proposal document: {e}")
            return False
    
    def search_similar_proposals(self,
                               query: str,
                               k: int = 5,
                               filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar proposals based on query
        
        Args:
            query: Search query (e.g., current RFP requirements)
            k: Number of results to return
            filter_metadata: Optional filters (client, year, document_type, etc.)
        
        Returns:
            List of similar proposal chunks with metadata
        """
        try:
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []
            
            # Perform similarity search
            if filter_metadata:
                results = self.vector_store.similarity_search_with_score(
                    query, 
                    k=k,
                    filter=filter_metadata
                )
            else:
                results = self.vector_store.similarity_search_with_score(query, k=k)
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": float(score),
                    "relevance": "high" if score > 0.8 else "medium" if score > 0.6 else "low"
                })
            
            logger.info(f"Found {len(formatted_results)} similar proposals for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching similar proposals: {e}")
            return []
    
    def get_context_for_analysis(self, 
                                requirements: List[str],
                                project_metadata: Dict = None) -> Dict[str, Any]:
        """
        Get relevant context from past proposals for current analysis
        
        Args:
            requirements: List of requirements from current RFP
            project_metadata: Current project information
        
        Returns:
            Dict with relevant context and suggestions
        """
        try:
            context = {
                "relevant_proposals": [],
                "similar_solutions": [],
                "risk_patterns": [],
                "pricing_references": [],
                "implementation_approaches": []
            }
            
            # Search for each requirement
            for requirement in requirements[:10]:  # Limit to avoid too many calls
                similar_docs = self.search_similar_proposals(
                    query=requirement,
                    k=3,
                    filter_metadata={"document_type": "proposal"}
                )
                
                for doc in similar_docs:
                    if doc["similarity_score"] > 0.7:  # High relevance threshold
                        context["relevant_proposals"].append({
                            "requirement": requirement,
                            "past_solution": doc["content"],
                            "metadata": doc["metadata"],
                            "confidence": doc["similarity_score"]
                        })
            
            # Search for technical solutions
            technical_query = " ".join(requirements)
            technical_docs = self.search_similar_proposals(
                query=technical_query,
                k=5,
                filter_metadata={"document_type": "technical"}
            )
            
            context["similar_solutions"] = technical_docs
            
            # Search for risk patterns
            risk_query = "risks challenges issues problems constraints"
            risk_docs = self.search_similar_proposals(
                query=risk_query,
                k=3,
                filter_metadata=None
            )
            
            context["risk_patterns"] = risk_docs
            
            logger.info(f"Generated context with {len(context['relevant_proposals'])} relevant proposals")
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for analysis: {e}")
            return {}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection"""
        try:
            if not self.vector_store:
                return {"error": "Vector store not initialized"}
            
            # Get basic stats by querying the database directly
            engine = create_engine(self.database_url)
            with engine.connect() as conn:
                # Count total documents
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM langchain_pg_embedding WHERE collection_id = "
                    "(SELECT uuid FROM langchain_pg_collection WHERE name = :collection_name)"
                ), {"collection_name": self.collection_name})
                total_documents = result.scalar() or 0
                
                # Get document types
                result = conn.execute(text(
                    "SELECT cmetadata->>'document_type' as doc_type, COUNT(*) as count "
                    "FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = :collection_name "
                    "GROUP BY cmetadata->>'document_type'"
                ), {"collection_name": self.collection_name})
                doc_types = dict(result.fetchall())
                
            return {
                "collection_name": self.collection_name,
                "total_documents": total_documents,
                "document_types": doc_types,
                "embeddings_model": getattr(self.embeddings, 'model', 'Unknown'),
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def delete_document(self, filter_metadata: Dict) -> bool:
        """Delete documents matching the filter criteria"""
        try:
            if not self.vector_store:
                return False
            
            # Note: PGVector doesn't have direct delete by metadata
            # This would need to be implemented by querying and deleting by IDs
            logger.warning("Delete functionality not fully implemented yet")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

# Singleton instance
vector_store_instance = None

def get_vector_store():
    """Get or create vector store instance with fallback"""
    global vector_store_instance
    
    if vector_store_instance is None:
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            try:
                vector_store_instance = TenderVectorStore(database_url)
                # Test if it works
                if vector_store_instance.vector_store is None:
                    raise Exception("Vector store initialization failed")
            except Exception as e:
                logger.warning(f"Failed to initialize advanced vector store: {e}")
                logger.info("Falling back to simple vector store")
                # Fallback to simple vector store
                try:
                    from simple_vector_store import get_simple_vector_store
                    return get_simple_vector_store()
                except Exception as fallback_error:
                    logger.error(f"Simple vector store also failed: {fallback_error}")
                    return None
        else:
            logger.error("DATABASE_URL not configured, using simple vector store")
            try:
                from simple_vector_store import get_simple_vector_store
                return get_simple_vector_store()
            except Exception as e:
                logger.error(f"Simple vector store failed: {e}")
                return None
            
    return vector_store_instance

def test_vector_store():
    """Test function to verify vector store setup"""
    try:
        vs = get_vector_store()
        if vs and vs.vector_store:
            # Add test document
            test_success = vs.add_proposal_document(
                content="This is a test proposal for cloud infrastructure development with AWS services, including EC2, S3, and RDS databases.",
                metadata={
                    "title": "Test Cloud Proposal",
                    "client": "Test Client",
                    "year": 2024,
                    "value": 100000,
                    "status": "won"
                },
                document_type="test"
            )
            
            if test_success:
                # Test search
                results = vs.search_similar_proposals("cloud infrastructure AWS", k=1)
                print(f"✅ Vector store test successful - found {len(results)} results")
                return True
            else:
                print("❌ Vector store test failed - could not add document")
                return False
        else:
            print("❌ Vector store not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Vector store test error: {e}")
        return False

if __name__ == "__main__":
    # Test the vector store
    test_vector_store()