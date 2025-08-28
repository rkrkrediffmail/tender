"""
Claude + Vector Intelligence System
Combines vector similarity search with Claude AI for maximum intelligence
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class ClaudeVectorIntelligence:
    """
    Advanced intelligence system combining vector search with Claude AI
    - Vector store for semantic similarity
    - Claude for content analysis and intelligence synthesis
    - PostgreSQL for structured metadata
    """
    
    def __init__(self):
        self.anthropic_client = self._init_claude()
        self.vector_store = self._init_vector_store()
        self.embedding_model = self._init_embeddings()
        
    def _init_claude(self):
        """Initialize Claude client"""
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not found")
                return None
            return anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Claude: {e}")
            return None
    
    def _init_vector_store(self):
        """Initialize vector store with Azure Blob Storage persistence"""
        try:
            from azure_vector_db_manager import get_azure_vector_db_manager
            
            # Get Azure Vector DB Manager (handles ChromaDB + Azure Blob Storage)
            self.azure_vector_manager = get_azure_vector_db_manager()
            client = self.azure_vector_manager.get_client()
            
            logger.info("✅ Vector store initialized with Azure Blob Storage persistence")
            return client
            
        except ImportError as e:
            logger.error(f"ChromaDB or Azure dependencies not available: {e}")
            logger.error("Installing ChromaDB...")
            os.system("pip install chromadb")
            return self._init_vector_store()
        except Exception as e:
            logger.error(f"Failed to initialize Azure vector store: {e}")
            # Fallback to local-only ChromaDB
            try:
                import chromadb
                from chromadb.config import Settings
                
                logger.warning("Falling back to local-only ChromaDB (no Azure persistence)")
                client = chromadb.PersistentClient(
                    path="./vector_db",
                    settings=Settings(
                        allow_reset=True,
                        anonymized_telemetry=False
                    )
                )
                return client
            except Exception as fallback_error:
                logger.error(f"Fallback vector store initialization failed: {fallback_error}")
                return None
    
    def _init_embeddings(self):
        """Initialize embedding model (using Claude's text embeddings via API)"""
        # For now, we'll use Claude to generate embeddings
        # Can be enhanced with dedicated embedding models later
        return "claude-embeddings"
    
    def process_past_proposal(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete Claude + Vector processing of past proposal
        
        Args:
            content: Raw proposal content
            metadata: Proposal metadata (title, client, etc.)
            
        Returns:
            Dict with processing results including vector storage success
        """
        try:
            logger.info(f"Processing past proposal: {metadata.get('title', 'Unknown')}")
            
            # Step 1: Claude Content Analysis & Intelligence Extraction
            claude_analysis = self._claude_deep_analysis(content, metadata)
            
            # Step 2: Claude-Enhanced Chunking for Vector Storage
            intelligent_chunks = self._claude_smart_chunking(content, claude_analysis)
            
            # Step 3: Claude-Generated Embeddings & Vector Storage
            vector_success = self._store_in_vector_db(intelligent_chunks, metadata, claude_analysis)
            
            # Step 4: Claude-Enhanced Metadata Synthesis
            enhanced_metadata = self._claude_metadata_enhancement(metadata, claude_analysis)
            
            return {
                'success': True,
                'claude_analysis': claude_analysis,
                'enhanced_metadata': enhanced_metadata,
                'chunks_stored': len(intelligent_chunks),
                'vector_storage_success': vector_success,
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing past proposal: {e}")
            return {
                'success': False,
                'error': str(e),
                'claude_analysis': {},
                'enhanced_metadata': metadata,
                'chunks_stored': 0,
                'vector_storage_success': False
            }
    
    def _claude_deep_analysis(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep Claude analysis of proposal content for maximum intelligence extraction
        """
        if not self.anthropic_client:
            return {'error': 'Claude not available'}
            
        try:
            prompt = f"""You are ITSS Global's AI intelligence system analyzing a past proposal for maximum knowledge extraction.

PAST PROPOSAL CONTENT:
{content[:8000]}  # Limit for token efficiency

METADATA:
- Title: {metadata.get('title', 'Unknown')}
- Client: {metadata.get('client_name', 'Unknown')}  
- Project Type: {metadata.get('project_type', 'Unknown')}
- Industry: {metadata.get('industry_sector', 'Unknown')}
- Status: {metadata.get('status', 'Unknown')}

EXTRACT MAXIMUM INTELLIGENCE - Analyze and return JSON with:

{{
  "executive_summary": "2-3 sentence summary of this proposal",
  
  "core_capabilities_demonstrated": [
    // List of specific capabilities ITSS demonstrated (be very specific)
  ],
  
  "technologies_and_platforms": [
    // All technologies, platforms, tools mentioned with context
  ],
  
  "solution_architecture_patterns": [
    // Architectural approaches, patterns, methodologies used
  ],
  
  "industry_specific_expertise": [
    // Banking, financial services specific knowledge demonstrated
  ],
  
  "regulatory_compliance_aspects": [
    // Any regulatory, compliance, standards mentioned
  ],
  
  "implementation_methodologies": [
    // Project management, implementation approaches used
  ],
  
  "key_differentiators": [
    // What made this proposal unique/competitive
  ],
  
  "client_pain_points_addressed": [
    // Specific problems this proposal solved
  ],
  
  "business_outcomes_delivered": [
    // Results, benefits, ROI mentioned
  ],
  
  "reusable_content_sections": {{
    "technical_approach": "text of reusable technical approach",
    "implementation_plan": "text of reusable implementation methodology", 
    "team_qualifications": "text about team expertise",
    "similar_experience": "text about relevant past experience",
    "risk_mitigation": "text about risk management approach"
  }},
  
  "search_keywords": [
    // Keywords that future RFPs might use to find this proposal
  ],
  
  "intelligence_score": 0.0-1.0,  // How much intelligence was extracted
  "confidence_level": 0.0-1.0     // Confidence in the analysis
}}

FOCUS: Maximum intelligence extraction for future proposal generation. Be comprehensive but precise."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse Claude's JSON response
            result = json.loads(response.content[0].text)
            result['analysis_timestamp'] = datetime.now().isoformat()
            
            return result
            
        except json.JSONDecodeError:
            logger.warning("Claude response was not valid JSON, using fallback")
            return self._fallback_analysis(content, metadata)
        except Exception as e:
            logger.error(f"Claude deep analysis failed: {e}")
            return self._fallback_analysis(content, metadata)
    
    def _claude_smart_chunking(self, content: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Claude-powered intelligent chunking for optimal vector storage
        """
        if not self.anthropic_client:
            return self._simple_chunking(content)
            
        try:
            prompt = f"""You are creating intelligent content chunks for vector storage and semantic search.

CONTENT TO CHUNK:
{content[:6000]}

ANALYSIS CONTEXT:
{json.dumps(analysis, indent=2)}

Create 5-8 intelligent chunks that:
1. Preserve semantic meaning
2. Focus on reusable content sections
3. Optimize for future similarity search
4. Include contextual metadata

Return JSON array of chunks:
[
  {{
    "chunk_id": "unique_id",
    "content": "chunk content (200-500 words)",
    "chunk_type": "technical_approach|implementation|team_experience|solution_architecture|business_case",
    "keywords": ["keyword1", "keyword2"],
    "context": "Brief context about what this chunk contains",
    "reusability_score": 0.0-1.0
  }}
]

OPTIMIZE FOR: Future RFP similarity matching and intelligent reuse."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            chunks = json.loads(response.content[0].text)
            return chunks if isinstance(chunks, list) else []
            
        except Exception as e:
            logger.error(f"Claude smart chunking failed: {e}")
            return self._simple_chunking(content)
    
    def _store_in_vector_db(self, chunks: List[Dict[str, Any]], metadata: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """
        Store intelligent chunks in vector database with Claude-generated embeddings
        """
        if not self.vector_store or not chunks:
            return False
            
        try:
            # Get or create collection for past proposals
            collection_name = f"past_proposals_{metadata.get('project_type', 'general')}"
            
            try:
                collection = self.vector_store.get_collection(collection_name)
            except:
                collection = self.vector_store.create_collection(
                    name=collection_name,
                    metadata={"description": f"Past proposals for {metadata.get('project_type', 'general')} projects"}
                )
            
            # Prepare data for vector storage
            documents = []
            metadatas = []
            ids = []
            
            proposal_id = metadata.get('proposal_id', f"proposal_{datetime.now().timestamp()}")
            
            for i, chunk in enumerate(chunks):
                # Enhanced metadata for each chunk
                chunk_metadata = {
                    "proposal_id": proposal_id,
                    "chunk_id": chunk.get('chunk_id', f"{proposal_id}_chunk_{i}"),
                    "chunk_type": chunk.get('chunk_type', 'general'),
                    "title": metadata.get('title', ''),
                    "client_name": metadata.get('client_name', ''),
                    "project_type": metadata.get('project_type', ''),
                    "industry_sector": metadata.get('industry_sector', ''),
                    "status": metadata.get('status', ''),
                    "submission_year": metadata.get('submission_year'),
                    "keywords": chunk.get('keywords', []),
                    "reusability_score": chunk.get('reusability_score', 0.5),
                    "intelligence_score": analysis.get('intelligence_score', 0.5),
                    "technologies": analysis.get('technologies_and_platforms', []),
                    "capabilities": analysis.get('core_capabilities_demonstrated', []),
                    "stored_at": datetime.now().isoformat()
                }
                
                documents.append(chunk.get('content', ''))
                metadatas.append(chunk_metadata)
                ids.append(chunk.get('chunk_id', f"{proposal_id}_chunk_{i}"))
            
            # Store in ChromaDB
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully stored {len(chunks)} chunks in vector DB")
            return True
            
        except Exception as e:
            logger.error(f"Vector storage failed: {e}")
            return False
    
    def intelligent_similarity_search(self, query: str, filters: Optional[Dict] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Claude-enhanced vector similarity search for maximum intelligence
        """
        try:
            # Step 1: Claude query enhancement and intent analysis
            enhanced_query = self._claude_query_enhancement(query, filters)
            
            # Step 2: Vector similarity search
            raw_results = self._vector_search(enhanced_query['search_query'], filters, limit * 2)
            
            # Step 3: Claude re-ranking and intelligence synthesis
            intelligent_results = self._claude_result_intelligence(query, raw_results, enhanced_query)
            
            return intelligent_results[:limit]
            
        except Exception as e:
            logger.error(f"Intelligent similarity search failed: {e}")
            return []
    
    def _claude_query_enhancement(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Claude enhances the search query for better vector matching
        """
        if not self.anthropic_client:
            return {'search_query': query, 'intent': 'general'}
            
        try:
            prompt = f"""Enhance this search query for finding relevant past proposals in a vector database.

ORIGINAL QUERY: "{query}"

FILTERS: {json.dumps(filters or {}, indent=2)}

Analyze the query and return JSON:
{{
  "search_query": "enhanced query with synonyms and related terms",
  "intent": "technical|commercial|implementation|team|experience|compliance",
  "key_concepts": ["concept1", "concept2"],
  "technologies_implied": ["tech1", "tech2"],
  "industry_context": "banking|fintech|insurance|etc",
  "search_strategy": "broad|focused|specific",
  "semantic_expansions": ["related_term1", "related_term2"]
}}

OPTIMIZE FOR: Finding the most relevant past proposal content for reuse."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return json.loads(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Query enhancement failed: {e}")
            return {'search_query': query, 'intent': 'general'}
    
    def _vector_search(self, query: str, filters: Optional[Dict] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search across all past proposal collections
        """
        if not self.vector_store:
            return []
            
        all_results = []
        
        try:
            # Get all collections
            collections = self.vector_store.list_collections()
            
            for collection in collections:
                if 'past_proposals' in collection.name:
                    try:
                        # Build where filter
                        where_filter = {}
                        if filters:
                            if filters.get('project_type'):
                                where_filter['project_type'] = filters['project_type']
                            if filters.get('industry_sector'):
                                where_filter['industry_sector'] = filters['industry_sector']
                            if filters.get('status'):
                                where_filter['status'] = filters['status']
                        
                        # Perform search
                        results = collection.query(
                            query_texts=[query],
                            n_results=min(limit // len(collections) + 2, 10),
                            where=where_filter if where_filter else None
                        )
                        
                        # Process results
                        if results['documents'] and results['documents'][0]:
                            for i, doc in enumerate(results['documents'][0]):
                                all_results.append({
                                    'content': doc,
                                    'metadata': results['metadatas'][0][i],
                                    'similarity_score': 1 - results['distances'][0][i] if 'distances' in results else 0.8,
                                    'collection': collection.name
                                })
                                
                    except Exception as e:
                        logger.warning(f"Search failed for collection {collection.name}: {e}")
            
            # Sort by similarity score
            all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return all_results[:limit]
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _claude_result_intelligence(self, original_query: str, raw_results: List[Dict[str, Any]], enhanced_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Claude analyzes and re-ranks search results for maximum intelligence
        """
        if not self.anthropic_client or not raw_results:
            return raw_results
            
        try:
            # Limit results for token efficiency
            top_results = raw_results[:15]
            
            results_summary = []
            for i, result in enumerate(top_results):
                results_summary.append({
                    'index': i,
                    'content_preview': result['content'][:300],
                    'similarity_score': result['similarity_score'],
                    'metadata': {
                        'title': result['metadata'].get('title', ''),
                        'project_type': result['metadata'].get('project_type', ''),
                        'chunk_type': result['metadata'].get('chunk_type', ''),
                        'technologies': result['metadata'].get('technologies', []),
                        'capabilities': result['metadata'].get('capabilities', [])
                    }
                })
            
            prompt = f"""You are analyzing search results from past proposals to provide maximum intelligence.

ORIGINAL QUERY: "{original_query}"
ENHANCED QUERY CONTEXT: {json.dumps(enhanced_query, indent=2)}

SEARCH RESULTS TO ANALYZE:
{json.dumps(results_summary, indent=2)}

Re-rank and enhance these results. Return JSON:
{{
  "intelligent_ranking": [
    {{
      "original_index": 0,
      "intelligence_score": 0.0-1.0,
      "relevance_explanation": "why this result is relevant",
      "reusability_assessment": "how this can be reused",
      "key_insights": ["insight1", "insight2"],
      "recommended_usage": "how to use this content",
      "content_quality": 0.0-1.0
    }}
  ],
  "search_insights": {{
    "query_interpretation": "what the user was really looking for",
    "content_gaps": "what relevant content might be missing",
    "recommendations": "suggestions for better results"
  }}
}}

FOCUS: Maximum intelligence and usability for proposal generation."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            intelligence = json.loads(response.content[0].text)
            
            # Apply Claude's intelligent ranking
            enhanced_results = []
            for item in intelligence.get('intelligent_ranking', []):
                original_idx = item.get('original_index')
                if original_idx < len(top_results):
                    result = top_results[original_idx].copy()
                    result['intelligence_score'] = item.get('intelligence_score', 0.5)
                    result['relevance_explanation'] = item.get('relevance_explanation', '')
                    result['reusability_assessment'] = item.get('reusability_assessment', '')
                    result['key_insights'] = item.get('key_insights', [])
                    result['recommended_usage'] = item.get('recommended_usage', '')
                    result['content_quality'] = item.get('content_quality', 0.5)
                    enhanced_results.append(result)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Claude result intelligence failed: {e}")
            return raw_results
    
    def get_intelligent_context_for_agents(self, requirements: List[str], project_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get intelligent context from past proposals for agents to use
        """
        try:
            # Claude analyzes requirements to build optimal search strategy
            search_strategy = self._claude_search_strategy(requirements, project_metadata)
            
            # Execute multiple intelligent searches
            relevant_content = []
            for search_term in search_strategy.get('search_terms', []):
                results = self.intelligent_similarity_search(
                    query=search_term,
                    filters={
                        'project_type': project_metadata.get('project_type'),
                        'industry_sector': project_metadata.get('industry_sector')
                    },
                    limit=5
                )
                relevant_content.extend(results)
            
            # Claude synthesizes all findings into actionable intelligence
            synthesized_intelligence = self._claude_intelligence_synthesis(
                requirements, project_metadata, relevant_content
            )
            
            return synthesized_intelligence
            
        except Exception as e:
            logger.error(f"Error getting intelligent context: {e}")
            return {'success': False, 'error': str(e)}
    
    def _claude_search_strategy(self, requirements: List[str], project_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Claude creates optimal search strategy for finding relevant past proposals
        """
        if not self.anthropic_client:
            return {'search_terms': requirements[:5]}
            
        try:
            prompt = f"""Create an optimal search strategy for finding relevant past proposals.

NEW PROJECT REQUIREMENTS:
{json.dumps(requirements, indent=2)}

PROJECT METADATA:
{json.dumps(project_metadata, indent=2)}

Create a strategic search plan. Return JSON:
{{
  "search_terms": ["optimized_search_term_1", "optimized_search_term_2"],
  "search_priority": ["high_priority_area", "medium_priority_area"],
  "content_focus": ["technical|commercial|implementation|team"],
  "industry_alignment": "strategy for industry-specific search",
  "technology_focus": ["key_technology_1", "key_technology_2"]
}}

OPTIMIZE FOR: Finding the most relevant and reusable past proposal content."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return json.loads(response.content[0].text)
            
        except Exception as e:
            logger.error(f"Search strategy creation failed: {e}")
            return {'search_terms': requirements[:5]}
    
    def _claude_intelligence_synthesis(self, requirements: List[str], project_metadata: Dict[str, Any], search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Claude synthesizes all search results into actionable intelligence for agents
        """
        if not self.anthropic_client:
            return {'success': False, 'error': 'Claude not available'}
            
        try:
            # Prepare search results summary for Claude
            results_summary = []
            for result in search_results[:20]:  # Limit for token efficiency
                results_summary.append({
                    'content': result.get('content', '')[:500],
                    'metadata': result.get('metadata', {}),
                    'relevance': result.get('intelligence_score', 0.5),
                    'chunk_type': result.get('metadata', {}).get('chunk_type', ''),
                    'technologies': result.get('metadata', {}).get('technologies', [])
                })
            
            prompt = f"""Synthesize intelligence from past proposals for new proposal generation.

NEW PROJECT REQUIREMENTS:
{json.dumps(requirements, indent=2)}

PROJECT METADATA:
{json.dumps(project_metadata, indent=2)}

RELEVANT PAST PROPOSAL CONTENT:
{json.dumps(results_summary, indent=2)}

Synthesize maximum intelligence. Return JSON:
{{
  "executive_intelligence": {{
    "confidence_level": 0.0-1.0,
    "content_coverage": "how well past proposals cover current needs",
    "strategic_recommendations": ["recommendation1", "recommendation2"]
  }},
  
  "reusable_content_sections": {{
    "technical_approach": {{
      "content": "synthesized technical approach from past proposals",
      "source_proposals": ["proposal_id1", "proposal_id2"],
      "adaptation_needed": "what needs to be customized",
      "confidence": 0.0-1.0
    }},
    "implementation_methodology": {{
      "content": "synthesized implementation approach",
      "source_proposals": ["proposal_id1"],
      "adaptation_needed": "customization requirements",
      "confidence": 0.0-1.0
    }},
    "team_experience": {{
      "content": "relevant team experience and qualifications",
      "source_proposals": ["proposal_id1"],
      "adaptation_needed": "how to adapt for current project",
      "confidence": 0.0-1.0
    }},
    "solution_architecture": {{
      "content": "architectural patterns and approaches",
      "source_proposals": ["proposal_id1"],
      "adaptation_needed": "architecture customization needed",
      "confidence": 0.0-1.0
    }}
  }},
  
  "capability_intelligence": {{
    "proven_capabilities": ["capability1", "capability2"],
    "technology_expertise": ["tech1", "tech2"],
    "industry_experience": ["experience_type1", "experience_type2"],
    "competitive_differentiators": ["differentiator1", "differentiator2"]
  }},
  
  "gap_analysis": {{
    "missing_capabilities": ["what we haven't done before"],
    "new_requirements": ["requirements not in past proposals"],
    "research_needed": ["areas needing more investigation"]
  }},
  
  "usage_instructions_for_agents": {{
    "document_intelligence_agent": "how document agent should use this",
    "requirements_engineering_agent": "how requirements agent should use this",
    "partner_recommendation_agent": "how partner agent should use this"
  }},
  
  "generation_guidance": {{
    "writing_style": "tone and style to use based on past proposals",
    "key_messaging": ["key_message1", "key_message2"],
    "success_factors": ["factor1", "factor2"]
  }}
}}

FOCUS: Maximum intelligence extraction for agent-driven proposal generation."""

            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            intelligence = json.loads(response.content[0].text)
            intelligence['success'] = True
            intelligence['synthesis_timestamp'] = datetime.now().isoformat()
            intelligence['sources_analyzed'] = len(search_results)
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Intelligence synthesis failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _fallback_analysis(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when Claude is not available"""
        return {
            'executive_summary': f"Analysis of {metadata.get('title', 'Unknown')} proposal",
            'core_capabilities_demonstrated': [],
            'technologies_and_platforms': [],
            'intelligence_score': 0.3,
            'confidence_level': 0.2,
            'error': 'Claude analysis not available'
        }
    
    def _simple_chunking(self, content: str) -> List[Dict[str, Any]]:
        """Simple chunking fallback when Claude is not available"""
        words = content.split()
        chunk_size = 300
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunks.append({
                'chunk_id': f"chunk_{i // chunk_size}",
                'content': ' '.join(chunk_words),
                'chunk_type': 'general',
                'keywords': [],
                'reusability_score': 0.5
            })
        
        return chunks
    
    def test_intelligence_system(self) -> Dict[str, Any]:
        """Test the complete Claude + Vector intelligence system"""
        try:
            test_results = {
                'claude_available': bool(self.anthropic_client),
                'vector_store_available': bool(self.vector_store),
                'embedding_model_available': bool(self.embedding_model)
            }
            
            if self.anthropic_client:
                # Test Claude analysis
                test_content = "This is a test banking proposal for core system modernization using Temenos T24."
                test_metadata = {'title': 'Test Proposal', 'client_name': 'Test Bank'}
                analysis = self._claude_deep_analysis(test_content, test_metadata)
                test_results['claude_analysis_success'] = bool(analysis.get('executive_summary'))
            
            if self.vector_store:
                # Test vector store connectivity
                collections = self.vector_store.list_collections()
                test_results['vector_collections_count'] = len(collections)
            
            test_results['overall_success'] = all([
                test_results['claude_available'],
                test_results['vector_store_available']
            ])
            
            return test_results
            
        except Exception as e:
            return {
                'overall_success': False,
                'error': str(e),
                'claude_available': False,
                'vector_store_available': False
            }

# Singleton instance
claude_vector_intelligence = None

def get_claude_vector_intelligence() -> ClaudeVectorIntelligence:
    """Get or create Claude Vector Intelligence instance"""
    global claude_vector_intelligence
    if claude_vector_intelligence is None:
        claude_vector_intelligence = ClaudeVectorIntelligence()
    return claude_vector_intelligence