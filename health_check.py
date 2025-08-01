"""Health check module for Azure App Service"""
from flask import jsonify
import os
import psycopg2
from datetime import datetime

def register_health_routes(app):
    """Register health check routes"""

    @app.route('/health')
    def health_check():
        """Basic health check"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'tender-analysis-system',
            'version': '1.0.0'
        }), 200

    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with dependencies"""

        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }

        # Check database connectivity
        try:
            database_url = os.environ.get('DATABASE_URL')
            if database_url:
                conn = psycopg2.connect(database_url)
                conn.close()
                health_status['checks']['database'] = 'healthy'
            else:
                health_status['checks']['database'] = 'not_configured'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check AI API keys
        health_status['checks']['anthropic_api'] = 'configured' if os.environ.get('ANTHROPIC_API_KEY') else 'not_configured'
        health_status['checks']['openai_api'] = 'configured' if os.environ.get('OPENAI_API_KEY') else 'not_configured'

        # Check storage
        health_status['checks']['azure_storage'] = 'configured' if os.environ.get('AZURE_STORAGE_CONNECTION_STRING') else 'not_configured'

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
