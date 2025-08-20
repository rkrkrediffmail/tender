"""
RFP Workflow Management System
Handles workflow transitions, notifications, and approvals
"""

import os
import smtplib
import json
import requests
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import List, Dict, Any, Optional
from models import db, Project, ProjectWorkflowHistory, ProjectStakeholder, NotificationLog, WorkflowStage, RFPTypeConfig
import logging

logger = logging.getLogger(__name__)

class WorkflowManager:
    """Manages RFP workflow transitions and notifications"""
    
    def __init__(self):
        self.email_config = self._get_email_config()
    
    def _get_email_config(self):
        """Get email configuration from environment"""
        return {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_username': os.getenv('SMTP_USERNAME'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL', os.getenv('SMTP_USERNAME')),
            'from_name': os.getenv('FROM_NAME', 'RFP Management System')
        }
    
    def get_available_rfp_types(self) -> List[Dict[str, Any]]:
        """Get all available RFP types"""
        types = RFPTypeConfig.query.filter_by(is_active=True).all()
        return [
            {
                'type_name': t.type_name,
                'display_name': t.display_name,
                'description': t.description,
                'default_stages': t.default_workflow_stages
            }
            for t in types
        ]
    
    def get_workflow_stages(self) -> List[Dict[str, Any]]:
        """Get all workflow stages"""
        stages = WorkflowStage.query.filter_by(is_active=True).order_by(WorkflowStage.stage_order).all()
        return [
            {
                'stage_name': s.stage_name,
                'display_name': s.display_name,
                'description': s.description,
                'requires_approval': s.requires_approval,
                'auto_advance': s.auto_advance,
                'next_stage': s.next_stage,
                'stage_order': s.stage_order
            }
            for s in stages
        ]
    
    def transition_workflow(self, project_id: str, to_stage: str, actor_email: str, 
                          actor_name: str = None, comments: str = None) -> Dict[str, Any]:
        """Transition project to next workflow stage"""
        try:
            project = Project.query.get(project_id)
            if not project:
                return {'success': False, 'error': 'Project not found'}
            
            from_stage = project.workflow_stage
            
            # Validate transition
            valid_transition = self._validate_transition(from_stage, to_stage)
            if not valid_transition['valid']:
                return {'success': False, 'error': valid_transition['error']}
            
            # Record transition
            history = ProjectWorkflowHistory(
                project_id=project_id,
                from_stage=from_stage,
                to_stage=to_stage,
                action=self._get_action_for_transition(from_stage, to_stage),
                actor_email=actor_email,
                actor_name=actor_name or actor_email,
                comments=comments
            )
            
            # Update project
            project.workflow_stage = to_stage
            project.updated_at = datetime.utcnow()
            if to_stage == 'approved':
                project.status = 'approved'
            elif to_stage == 'rejected':
                project.status = 'rejected'
            
            db.session.add(history)
            db.session.commit()
            
            # Send notifications
            self._send_stage_notifications(project, from_stage, to_stage, actor_email, comments)
            
            logger.info(f"Project {project_id} transitioned from {from_stage} to {to_stage} by {actor_email}")
            
            return {
                'success': True,
                'from_stage': from_stage,
                'to_stage': to_stage,
                'actor': actor_email
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Workflow transition error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_transition(self, from_stage: str, to_stage: str) -> Dict[str, Any]:
        """Validate if transition is allowed"""
        # Get stage configuration
        current_stage = WorkflowStage.query.filter_by(stage_name=from_stage).first()
        target_stage = WorkflowStage.query.filter_by(stage_name=to_stage).first()
        
        if not target_stage:
            return {'valid': False, 'error': f'Invalid target stage: {to_stage}'}
        
        if not current_stage:
            # First transition (created state)
            if to_stage in ['authorized', 'created']:
                return {'valid': True}
            return {'valid': False, 'error': 'First transition must be to authorized stage'}
        
        # Check if transition is allowed
        allowed_next_stages = [current_stage.next_stage, current_stage.rejection_stage, 'rejected']
        if to_stage not in allowed_next_stages:
            return {'valid': False, 'error': f'Cannot transition from {from_stage} to {to_stage}'}
        
        return {'valid': True}
    
    def _get_action_for_transition(self, from_stage: str, to_stage: str) -> str:
        """Determine action type based on transition"""
        if to_stage == 'rejected':
            return 'reject'
        elif from_stage == 'created':
            return 'submit'
        else:
            return 'approve'
    
    def add_stakeholder(self, project_id: str, email: str, name: str = None, 
                       role: str = 'approver', stage: str = 'authorized',
                       notification_preference: str = 'email',
                       teams_webhook: str = None) -> Dict[str, Any]:
        """Add stakeholder to project"""
        try:
            # Check if stakeholder already exists
            existing = ProjectStakeholder.query.filter_by(
                project_id=project_id, 
                email=email, 
                stage=stage
            ).first()
            
            if existing:
                return {'success': False, 'error': 'Stakeholder already exists for this stage'}
            
            stakeholder = ProjectStakeholder(
                project_id=project_id,
                email=email,
                name=name or email,
                role=role,
                stage=stage,
                notification_preference=notification_preference,
                teams_webhook_url=teams_webhook
            )
            
            db.session.add(stakeholder)
            db.session.commit()
            
            logger.info(f"Added stakeholder {email} to project {project_id} for stage {stage}")
            
            return {
                'success': True,
                'stakeholder_id': stakeholder.id,
                'email': email,
                'role': role,
                'stage': stage
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding stakeholder: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_project_stakeholders(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all stakeholders for a project"""
        stakeholders = ProjectStakeholder.query.filter_by(project_id=project_id).all()
        return [
            {
                'id': s.id,
                'email': s.email,
                'name': s.name,
                'role': s.role,
                'stage': s.stage,
                'notification_preference': s.notification_preference,
                'has_approved': s.has_approved,
                'approved_at': s.approved_at.isoformat() if s.approved_at else None,
                'comments': s.comments
            }
            for s in stakeholders
        ]
    
    def get_workflow_history(self, project_id: str) -> List[Dict[str, Any]]:
        """Get workflow history for a project"""
        history = ProjectWorkflowHistory.query.filter_by(project_id=project_id)\
                                            .order_by(ProjectWorkflowHistory.created_at.desc()).all()
        return [
            {
                'id': h.id,
                'from_stage': h.from_stage,
                'to_stage': h.to_stage,
                'action': h.action,
                'actor_email': h.actor_email,
                'actor_name': h.actor_name,
                'comments': h.comments,
                'created_at': h.created_at.isoformat()
            }
            for h in history
        ]
    
    def _send_stage_notifications(self, project: Project, from_stage: str, 
                                to_stage: str, actor_email: str, comments: str = None):
        """Send notifications for stage transitions"""
        try:
            # Get stakeholders for the new stage
            stakeholders = ProjectStakeholder.query.filter_by(
                project_id=project.id,
                stage=to_stage
            ).all()
            
            if not stakeholders:
                logger.warning(f"No stakeholders configured for stage {to_stage} in project {project.id}")
                return
            
            # Prepare notification content
            subject = f"RFP Action Required: {project.name} - {to_stage.title()} Stage"
            message = self._create_notification_message(project, from_stage, to_stage, actor_email, comments)
            
            # Send to each stakeholder
            for stakeholder in stakeholders:
                if stakeholder.notification_preference in ['email', 'both']:
                    self._send_email_notification(stakeholder.email, subject, message, project.id)
                
                if stakeholder.notification_preference in ['teams', 'both'] and stakeholder.teams_webhook_url:
                    self._send_teams_notification(stakeholder.teams_webhook_url, subject, message, project.id)
            
        except Exception as e:
            logger.error(f"Error sending stage notifications: {e}")
    
    def _create_notification_message(self, project: Project, from_stage: str, 
                                   to_stage: str, actor_email: str, comments: str = None) -> str:
        """Create notification message content"""
        message = f"""
RFP Workflow Update

Project: {project.name}
RFP Type: {project.rfp_type.title()}
Client: {project.client_name or 'Not specified'}

Status Change: {from_stage.title()} → {to_stage.title()}
Action taken by: {actor_email}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        if comments:
            message += f"Comments: {comments}\n\n"
        
        if to_stage == 'approved':
            message += "✅ This RFP has been APPROVED and can proceed.\n"
        elif to_stage == 'rejected':
            message += "❌ This RFP has been REJECTED.\n"
        else:
            message += f"⏳ Action required: This RFP is now awaiting {to_stage} approval.\n"
        
        # Add project link (assuming web interface)
        base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        message += f"\nView project: {base_url}/project/{project.id}\n"
        
        return message
    
    def _send_email_notification(self, recipient_email: str, subject: str, 
                               message: str, project_id: str):
        """Send email notification"""
        try:
            if not self.email_config['smtp_username'] or not self.email_config['smtp_password']:
                logger.warning("Email not configured - skipping email notification")
                return
            
            msg = MimeMultipart()
            msg['From'] = f"{self.email_config['from_name']} <{self.email_config['from_email']}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            msg.attach(MimeText(message, 'plain'))
            
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                server.send_message(msg)
            
            # Log notification
            self._log_notification(project_id, recipient_email, 'email', 'stage_change', 
                                 subject, message, 'sent')
            
            logger.info(f"Email sent to {recipient_email}")
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {e}")
            self._log_notification(project_id, recipient_email, 'email', 'stage_change',
                                 subject, message, 'failed', str(e))
    
    def _send_teams_notification(self, webhook_url: str, subject: str, 
                               message: str, project_id: str):
        """Send Microsoft Teams notification"""
        try:
            # Teams adaptive card format
            card = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": subject,
                "sections": [{
                    "activityTitle": subject,
                    "activitySubtitle": "RFP Management System",
                    "activityImage": "https://adaptivecards.io/content/cats/1.png",  # Replace with your logo
                    "facts": [
                        {"name": "Type", "value": "RFP Workflow Update"},
                        {"name": "Time", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    ],
                    "text": message
                }],
                "potentialAction": [{
                    "@type": "OpenUri",
                    "name": "View Project",
                    "targets": [{"os": "default", "uri": f"{os.getenv('BASE_URL', 'http://localhost:5001')}/project/{project_id}"}]
                }]
            }
            
            response = requests.post(webhook_url, json=card, timeout=10)
            response.raise_for_status()
            
            # Log notification
            self._log_notification(project_id, webhook_url, 'teams', 'stage_change',
                                 subject, message, 'sent')
            
            logger.info(f"Teams notification sent to webhook")
            
        except Exception as e:
            logger.error(f"Error sending Teams notification: {e}")
            self._log_notification(project_id, webhook_url, 'teams', 'stage_change',
                                 subject, message, 'failed', str(e))
    
    def _log_notification(self, project_id: str, recipient: str, notification_type: str,
                         event_type: str, subject: str, message: str, 
                         status: str, error_message: str = None):
        """Log notification attempt"""
        try:
            log_entry = NotificationLog(
                project_id=project_id,
                recipient_email=recipient,
                notification_type=notification_type,
                event_type=event_type,
                subject=subject,
                message=message,
                status=status,
                error_message=error_message,
                sent_at=datetime.utcnow() if status == 'sent' else None
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging notification: {e}")

# Global workflow manager instance
workflow_manager = WorkflowManager()

def setup_default_config():
    """Setup default RFP types and workflow stages"""
    try:
        # Default RFP Types
        default_types = [
            {
                'type_name': 'implementation',
                'display_name': 'New Implementation',
                'description': 'Brand new system or solution implementation',
                'stages': ['created', 'authorized', 'validated', 'approved']
            },
            {
                'type_name': 'upgrade',
                'display_name': 'System Upgrade',
                'description': 'Upgrading existing systems or solutions',
                'stages': ['created', 'authorized', 'validated', 'approved']
            },
            {
                'type_name': 'integration',
                'display_name': 'System Integration',
                'description': 'Integration with existing systems',
                'stages': ['created', 'authorized', 'validated', 'approved']
            },
            {
                'type_name': 'maintenance',
                'display_name': 'Maintenance & Support',
                'description': 'Ongoing maintenance and support services',
                'stages': ['created', 'authorized', 'approved']  # Simpler workflow
            },
            {
                'type_name': 'custom',
                'display_name': 'Custom Solution',
                'description': 'Custom-built solutions and applications',
                'stages': ['created', 'authorized', 'validated', 'approved']
            }
        ]
        
        for type_config in default_types:
            existing = RFPTypeConfig.query.filter_by(type_name=type_config['type_name']).first()
            if not existing:
                rfp_type = RFPTypeConfig(
                    type_name=type_config['type_name'],
                    display_name=type_config['display_name'],
                    description=type_config['description'],
                    default_workflow_stages=type_config['stages']
                )
                db.session.add(rfp_type)
        
        # Default Workflow Stages
        default_stages = [
            {
                'stage_name': 'created',
                'display_name': 'Created',
                'description': 'RFP has been created and is ready for submission',
                'requires_approval': False,
                'auto_advance': False,
                'next_stage': 'authorized',
                'stage_order': 1
            },
            {
                'stage_name': 'authorized',
                'display_name': 'Authorization Required',
                'description': 'RFP requires initial authorization to proceed',
                'requires_approval': True,
                'auto_advance': False,
                'next_stage': 'validated',
                'stage_order': 2
            },
            {
                'stage_name': 'validated',
                'display_name': 'Validation Required',
                'description': 'RFP requires technical and business validation',
                'requires_approval': True,
                'auto_advance': False,
                'next_stage': 'approved',
                'stage_order': 3
            },
            {
                'stage_name': 'approved',
                'display_name': 'Approved',
                'description': 'RFP has been fully approved and can proceed',
                'requires_approval': False,
                'auto_advance': False,
                'next_stage': None,
                'stage_order': 4
            },
            {
                'stage_name': 'rejected',
                'display_name': 'Rejected',
                'description': 'RFP has been rejected and cannot proceed',
                'requires_approval': False,
                'auto_advance': False,
                'next_stage': None,
                'stage_order': 99
            }
        ]
        
        for stage_config in default_stages:
            existing = WorkflowStage.query.filter_by(stage_name=stage_config['stage_name']).first()
            if not existing:
                stage = WorkflowStage(
                    stage_name=stage_config['stage_name'],
                    display_name=stage_config['display_name'],
                    description=stage_config['description'],
                    requires_approval=stage_config['requires_approval'],
                    auto_advance=stage_config['auto_advance'],
                    next_stage=stage_config['next_stage'],
                    stage_order=stage_config['stage_order']
                )
                db.session.add(stage)
        
        db.session.commit()
        logger.info("✅ Default workflow configuration created")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting up default config: {e}")