"""
Simple Vector Store Implementation
Fallback when LangChain/pgvector dependencies are problematic
Uses scikit-learn for similarity search without external vector database
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import uuid

logger = logging.getLogger(__name__)

class SimpleTenderVectorStore:
    """
    Simple vector store using TF-IDF and cosine similarity
    No external dependencies beyond scikit-learn
    """
    
    def __init__(self, storage_path: str = "vector_storage"):
        self.storage_path = storage_path
        self.documents = []
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.vectors = None
        self.is_fitted = False
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
        
        # Load existing data
        self._load_data()
    
    def add_proposal_document(self, 
                            content: str, 
                            metadata: Dict[str, Any],
                            document_type: str = "proposal") -> bool:
        """
        Add a past proposal document to the simple vector store
        """
        try:
            # Create document entry
            doc_id = str(uuid.uuid4())
            document = {
                'id': doc_id,
                'content': content,
                'metadata': {
                    **metadata,
                    'document_type': document_type,
                    'added_at': datetime.now().isoformat()
                }
            }
            
            self.documents.append(document)
            
            # Refit vectorizer with new documents
            self._refit_vectorizer()
            
            # Save to disk
            self._save_data()
            
            logger.info(f"Added document {doc_id} to simple vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document to simple vector store: {e}")
            return False
    
    def search_similar_proposals(self,
                               query: str,
                               k: int = 5,
                               filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar proposals using TF-IDF similarity
        """
        try:
            if not self.documents or not self.is_fitted:
                return []
            
            # Vectorize query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.vectors)[0]
            
            # Get top k indices
            top_indices = np.argsort(similarities)[::-1][:k]
            
            results = []
            for idx in top_indices:
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    similarity_score = float(similarities[idx])
                    
                    # Apply metadata filters if provided
                    if filter_metadata:
                        match = True
                        for key, value in filter_metadata.items():
                            if doc['metadata'].get(key) != value:
                                match = False
                                break
                        if not match:
                            continue
                    
                    results.append({
                        'content': doc['content'][:500] + '...' if len(doc['content']) > 500 else doc['content'],
                        'metadata': doc['metadata'],
                        'similarity_score': similarity_score,
                        'relevance': 'high' if similarity_score > 0.3 else 'medium' if similarity_score > 0.1 else 'low'
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching simple vector store: {e}")
            return []
    
    def get_context_for_analysis(self, 
                                requirements: List[str],
                                project_metadata: Dict = None) -> Dict[str, Any]:
        """
        Get relevant context from past proposals
        """
        try:
            context = {
                "relevant_proposals": [],
                "similar_solutions": [],
                "risk_patterns": [],
                "pricing_references": []
            }
            
            # Search for each requirement
            for requirement in requirements[:5]:  # Limit to avoid too many searches
                similar_docs = self.search_similar_proposals(
                    query=requirement,
                    k=2,
                    filter_metadata={"document_type": "proposal"}
                )
                
                for doc in similar_docs:
                    if doc["similarity_score"] > 0.2:  # Reasonable threshold for TF-IDF
                        context["relevant_proposals"].append({
                            "requirement": requirement,
                            "past_solution": doc["content"],
                            "metadata": doc["metadata"],
                            "confidence": doc["similarity_score"]
                        })
            
            # Search for technical solutions
            if requirements:
                technical_query = " ".join(requirements[:3])
                technical_docs = self.search_similar_proposals(
                    query=technical_query,
                    k=3
                )
                context["similar_solutions"] = technical_docs
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return {}
    
    def _refit_vectorizer(self):
        """Refit the vectorizer with all documents"""
        try:
            if not self.documents:
                return
            
            # Extract all content
            all_content = [doc['content'] for doc in self.documents]
            
            # Fit vectorizer and transform documents
            self.vectors = self.vectorizer.fit_transform(all_content)
            self.is_fitted = True
            
        except Exception as e:
            logger.error(f"Error refitting vectorizer: {e}")
    
    def _save_data(self):
        """Save documents and vectorizer to disk"""
        try:
            # Save documents
            with open(os.path.join(self.storage_path, 'documents.json'), 'w') as f:
                json.dump(self.documents, f, indent=2)
            
            # Save vectorizer
            with open(os.path.join(self.storage_path, 'vectorizer.pkl'), 'wb') as f:
                pickle.dump(self.vectorizer, f)
            
            # Save vectors if fitted
            if self.is_fitted and self.vectors is not None:
                with open(os.path.join(self.storage_path, 'vectors.pkl'), 'wb') as f:
                    pickle.dump(self.vectors, f)
                    
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def _load_data(self):
        """Load documents and vectorizer from disk"""
        try:
            # Load documents
            docs_path = os.path.join(self.storage_path, 'documents.json')
            if os.path.exists(docs_path):
                with open(docs_path, 'r') as f:
                    self.documents = json.load(f)
            
            # Load vectorizer
            vectorizer_path = os.path.join(self.storage_path, 'vectorizer.pkl')
            if os.path.exists(vectorizer_path):
                with open(vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
            
            # Load vectors
            vectors_path = os.path.join(self.storage_path, 'vectors.pkl')
            if os.path.exists(vectors_path):
                with open(vectors_path, 'rb') as f:
                    self.vectors = pickle.load(f)
                    self.is_fitted = True
                    
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            doc_types = {}
            for doc in self.documents:
                doc_type = doc['metadata'].get('document_type', 'unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            return {
                'collection_name': 'simple_tender_proposals',
                'total_documents': len(self.documents),
                'document_types': doc_types,
                'vectorizer_features': getattr(self.vectorizer, 'max_features', 0),
                'is_fitted': self.is_fitted,
                'status': 'active'
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}

# Singleton instance
simple_vector_store = None

def get_simple_vector_store() -> SimpleTenderVectorStore:
    """Get or create simple vector store instance"""
    global simple_vector_store
    
    if simple_vector_store is None:
        simple_vector_store = SimpleTenderVectorStore()
        
    return simple_vector_store

def test_simple_vector_store():
    """Test the simple vector store"""
    try:
        vs = get_simple_vector_store()
        
        # Add test document
        success = vs.add_proposal_document(
            content="This is a test proposal for cloud infrastructure development with AWS services including EC2 and S3.",
            metadata={
                "title": "Test Cloud Proposal",
                "client_name": "Test Client",
                "project_type": "infrastructure",
                "status": "test"
            },
            document_type="test"
        )
        
        if success:
            # Test search
            results = vs.search_similar_proposals("cloud infrastructure AWS", k=1)
            print(f"✅ Simple vector store test successful - found {len(results)} results")
            if results:
                print(f"   Best match: {results[0]['similarity_score']:.3f} similarity")
            return True
        else:
            print("❌ Simple vector store test failed")
            return False
            
    except Exception as e:
        print(f"❌ Simple vector store test error: {e}")
        return False

if __name__ == "__main__":
    test_simple_vector_store()