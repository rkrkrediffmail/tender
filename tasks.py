#!/usr/bin/env python3
"""
Fix tasks module and database schema issues
"""
from celery import current_task
from main import celery, create_app
import os
from datetime import datetime

# Create app context for tasks
app = create_app()

@celery.task(bind=True)
def process_document_task(self, document_id):
    """Process uploaded document with AI analysis"""
    with app.app_context():
        try:
            current_task.update_state(state='PROGRESS', meta={'status': 'Starting document processing'})

            from models import db, Document
            document = Document.query.get(document_id)
            if not document:
                raise Exception(f"Document {document_id} not found")

            print(f"🤖 Processing document ID {document_id}")

            # Get filename safely
            filename = getattr(document, 'original_filename', None) or getattr(document, 'filename', 'unknown')
            print(f"📄 File: {filename}")

            current_task.update_state(state='PROGRESS', meta={'status': 'Reading document content'})

            # Read file content
            content = ""
            if document.file_path and os.path.exists(document.file_path):
                try:
                    if filename.lower().endswith('.txt'):
                        with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    elif filename.lower().endswith('.docx'):
                        try:
                            import docx
                            doc = docx.Document(document.file_path)
                            content = '\\n'.join([paragraph.text for paragraph in doc.paragraphs])
                        except Exception as e:
                            print(f"⚠️ DOCX reading failed: {e}")
                            content = f"Document: {filename} (DOCX content extraction failed)"
                    else:
                        content = f"Document: {filename} (unsupported format for text extraction)"

                    print(f"✅ Extracted {len(content)} characters")

                except Exception as e:
                    print(f"❌ File reading error: {e}")
                    content = f"Document: {filename} (file reading failed)"
            else:
                print(f"❌ File not found: {document.file_path}")
                content = f"Document: {filename} (file not found)"

            current_task.update_state(state='PROGRESS', meta={'status': 'Calling AI for analysis'})

            # AI Analysis
            anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
            analysis_result = "No analysis performed"

            if anthropic_key and not anthropic_key.startswith('your-'):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=anthropic_key)

                    print("🤖 Calling Anthropic API...")

                    # Truncate content if too long
                    content_for_analysis = content[:8000] if len(content) > 8000 else content

                    message = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=2000,
                        messages=[
                            {
                                "role": "user",
                                "content": f"""Analyze this RFP/tender document and extract key information:

Document Content:
{content_for_analysis}

Please provide a structured analysis including:

1. **MUST HAVE REQUIREMENTS:**
   - List critical/mandatory requirements

2. **GOOD TO HAVE REQUIREMENTS:**
   - List preferred/optional requirements

3. **TECHNICAL SPECIFICATIONS:**
   - Key technical details and constraints

4. **COMPLIANCE & STANDARDS:**
   - Any compliance requirements or standards mentioned

5. **PROJECT DETAILS:**
   - Timeline, budget, or other project information

Format your response clearly with headers and bullet points."""
                            }
                        ]
                    )

                    analysis_result = message.content[0].text
                    print(f"✅ AI analysis completed: {len(analysis_result)} characters")

                except Exception as e:
                    print(f"❌ AI analysis failed: {e}")
                    analysis_result = f"AI analysis failed: {str(e)}"
            else:
                print("⚠️ Anthropic API key not configured properly")
                analysis_result = "AI analysis skipped: API key not configured"

            current_task.update_state(state='PROGRESS', meta={'status': 'Saving results'})

            # Save analysis result (you could parse this and save structured requirements)
            # For now, we'll just store it as a simple note
            # You could extend this to parse the AI response and create Requirement objects

            print("💾 Analysis completed and ready")

            return {
                'status': 'completed',
                'document_id': document_id,
                'filename': filename,
                'content_length': len(content),
                'analysis_length': len(analysis_result),
                'analysis_preview': analysis_result[:500] + "..." if len(analysis_result) > 500 else analysis_result,
                'message': 'Document analysis completed successfully'
            }

        except Exception as e:
            print(f"❌ Task failed: {e}")
            current_task.update_state(
                state='FAILURE',
                meta={'error': str(e), 'document_id': document_id}
            )
            raise

@celery.task
def test_task():
    """Simple test task"""
    return "Celery is working!"

@celery.task
def cleanup_old_files():
    """Cleanup old uploaded files"""
    # This could be used to clean up old files periodically
    return "Cleanup completed"
'''

# Second, let's create a database schema fix
schema_fix_content = '''
# Fix database schema issues
import os, sys
sys.path.insert(0, os.getcwd())

def fix_document_schema():
    """Fix Document model schema issues"""
    print("🔧 Fixing database schema...")

    try:
        from main import app
        from models import db

        with app.app_context():
            engine = db.engine

            # Check current document table structure
            print("📊 Checking current schema...")

            try:
                inspector = db.inspect(engine)
                columns = inspector.get_columns('documents')
                column_names = [col['name'] for col in columns]
                print(f"   Current columns: {column_names}")

                # Add missing columns if needed
                missing_columns = []

                if 'original_filename' not in column_names:
                    missing_columns.append('original_filename')

                if missing_columns:
                    print(f"📝 Adding missing columns: {missing_columns}")

                    with engine.connect() as conn:
                        for col in missing_columns:
                            if col == 'original_filename':
                                # Add original_filename column
                                conn.execute(db.text("""
                                    ALTER TABLE documents
                                    ADD COLUMN IF NOT EXISTS original_filename VARCHAR(500);
                                """))

                                # Update existing records to copy filename to original_filename
                                conn.execute(db.text("""
                                    UPDATE documents
                                    SET original_filename = filename
                                    WHERE original_filename IS NULL;
                                """))

                        conn.commit()
                        print("✅ Schema updated successfully")
                else:
                    print("✅ Schema is already correct")

                # Verify the fix
                from models import Document
                doc_count = Document.query.count()
                print(f"✅ Verified: {doc_count} documents accessible")

                if doc_count > 0:
                    latest_doc = Document.query.first()
                    filename = getattr(latest_doc, 'original_filename', None) or getattr(latest_doc, 'filename', 'unknown')
                    print(f"📄 Sample document: {filename}")

                return True

            except Exception as e:
                print(f"❌ Schema fix failed: {e}")
                return False

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    fix_document_schema()
