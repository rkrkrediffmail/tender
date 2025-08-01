# agents/base_agent.py
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

import openai
from anthropic import Anthropic
from models import db, Agent, AgentTask, AgentMessage, SystemLog

class BaseAgent(ABC):
    """Base class for all AI agents"""

    def __init__(self, agent_id: int, config: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = logging.getLogger(f"Agent-{agent_id}")

        # Load agent data from database
        self.agent_data = Agent.query.get(agent_id)
        if not self.agent_data:
            raise ValueError(f"Agent with ID {agent_id} not found")

        # Initialize AI clients
        self.anthropic_client = Anthropic(api_key=self.config.get('anthropic_api_key'))
        self.openai_client = openai.Client(api_key=self.config.get('openai_api_key'))

    async def process_task(self, task_id: str) -> Dict[str, Any]:
        """Main task processing method"""

        # Get task from database
        task = AgentTask.query.filter_by(task_id=task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update task status
        task.status = 'in_progress'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Log task start
            self._log_event('INFO', 'task_started', f"Started processing task: {task.title}")

            # Execute specific agent logic
            result = await self._execute_task(task)

            # Update task completion
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            task.output_data = result
            task.progress_percentage = 100

            # Calculate actual duration
            if task.started_at:
                duration = (datetime.utcnow() - task.started_at).total_seconds() / 60
                task.actual_duration = int(duration)

            db.session.commit()

            self._log_event('INFO', 'task_completed', f"Completed task: {task.title}")
            return result

        except Exception as e:
            # Handle task failure
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            db.session.commit()

            self._log_event('ERROR', 'task_failed', f"Task failed: {task.title}, Error: {str(e)}")
            raise

    @abstractmethod
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Agent-specific task execution logic"""
        pass

    async def call_claude(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000) -> str:
        """Call Claude API with error handling and logging"""

        try:
            system = system_prompt or self.agent_data.system_prompt

            response = await self.anthropic_client.messages.create(
                model=self.agent_data.model_name or "claude-sonnet-4",
                max_tokens=max_tokens,
                temperature=self.agent_data.temperature or 0.3,
                system=system,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.content[0].text

        except Exception as e:
            self._log_event('ERROR', 'api_call_failed', f"Claude API call failed: {str(e)}")
            raise

    async def call_openai_reasoning(self, problem: str) -> str:
        """Call OpenAI o1 for complex reasoning tasks"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="o1-preview",
                messages=[
                    {"role": "user", "content": problem}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            self._log_event('ERROR', 'api_call_failed', f"OpenAI API call failed: {str(e)}")
            raise

    async def send_message(self, recipient_agent_id: int, message_type: str,
                          subject: str, content: str, payload: Dict = None) -> str:
        """Send message to another agent"""

        message = AgentMessage(
            agent_id=self.agent_id,
            recipient_agent_id=recipient_agent_id,
            message_type=message_type,
            subject=subject,
            content=content,
            payload=payload or {}
        )

        db.session.add(message)
        db.session.commit()

        self._log_event('INFO', 'message_sent', f"Sent {message_type} to Agent {recipient_agent_id}")
        return message.message_id

    async def get_messages(self, unread_only: bool = True) -> List[AgentMessage]:
        """Get messages for this agent"""

        query = AgentMessage.query.filter_by(recipient_agent_id=self.agent_id)
        if unread_only:
            query = query.filter_by(status='sent')

        return query.order_by(AgentMessage.created_at.desc()).all()

    def _log_event(self, level: str, event_type: str, message: str, details: Dict = None):
        """Log system events"""

        log_entry = SystemLog(
            log_level=level,
            component=self.agent_data.name,
            event_type=event_type,
            message=message,
            details=details or {},
            agent_id=self.agent_id
        )

        db.session.add(log_entry)
        db.session.commit()
