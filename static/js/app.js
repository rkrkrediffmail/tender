// AI Tender Analysis System - Main JavaScript File

(function() {
    'use strict';

    // Global application state
    const App = {
        agents: new Map(),
        workflows: new Map(),
        notifications: [],
        realTimeUpdates: true,
        refreshInterval: 5000
    };

    // Initialize application when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeApp();
    });

    function initializeApp() {
        console.log('AI Tender Analysis System - Initializing...');
        
        // Initialize components
        initializeAgentMonitoring();
        initializeWorkflowVisualization();
        initializeCommunicationFeed();
        initializeDocumentUpload();
        initializeQualityAssurance();
        initializeNotifications();
        initializeRealTimeUpdates();
        
        console.log('AI Tender Analysis System - Ready');
    }

    // Agent Monitoring Functionality
    function initializeAgentMonitoring() {
        const agentCards = document.querySelectorAll('.agent-card, .agent-monitor');
        
        agentCards.forEach(card => {
            // Add hover effects
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 0.5rem 1rem rgba(0, 0, 0, 0.15)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
            
            // Add click functionality
            card.addEventListener('click', function() {
                const agentName = this.querySelector('h6').textContent;
                showAgentDetails(agentName);
            });
        });

        // Update agent statuses
        updateAgentStatuses();
        
        // Start performance monitoring
        startPerformanceMonitoring();
    }

    function updateAgentStatuses() {
        const statusIndicators = document.querySelectorAll('.agent-status, .status-indicator');
        
        statusIndicators.forEach(indicator => {
            // Simulate real-time status updates
            const statuses = ['online', 'processing', 'waiting'];
            const currentStatus = indicator.classList.contains('online') ? 'online' : 
                                 indicator.classList.contains('processing') ? 'processing' : 'waiting';
            
            // Randomly update status (in real app, this would come from server)
            if (Math.random() < 0.1) { // 10% chance of status change
                indicator.className = indicator.className.replace(/\b(online|processing|waiting|pending)\b/g, '');
                const newStatus = statuses[Math.floor(Math.random() * statuses.length)];
                indicator.classList.add(newStatus);
            }
        });
    }

    function startPerformanceMonitoring() {
        // Update performance metrics
        setInterval(() => {
            updatePerformanceMetrics();
            updateResourceUsage();
            updateAgentStatuses();
        }, App.refreshInterval);
    }

    function updatePerformanceMetrics() {
        const metricNumbers = document.querySelectorAll('.metric-number');
        
        metricNumbers.forEach(metric => {
            if (metric.textContent.includes('s')) { // Response time
                const currentValue = parseFloat(metric.textContent);
                const variation = (Math.random() - 0.5) * 0.2; // ±0.1s variation
                const newValue = Math.max(0.1, currentValue + variation).toFixed(1);
                metric.textContent = newValue + 's';
                
                // Update color based on performance
                metric.className = metric.className.replace(/text-(success|warning|danger)/g, '');
                if (newValue <= 2.0) {
                    metric.classList.add('text-success');
                } else if (newValue <= 3.0) {
                    metric.classList.add('text-warning');
                } else {
                    metric.classList.add('text-danger');
                }
            }
        });
    }

    function updateResourceUsage() {
        const progressBars = document.querySelectorAll('.resource-item .progress-bar');
        
        progressBars.forEach(bar => {
            const currentWidth = parseInt(bar.style.width);
            const variation = (Math.random() - 0.5) * 10; // ±5% variation
            const newWidth = Math.max(5, Math.min(95, currentWidth + variation));
            
            bar.style.width = newWidth + '%';
            bar.parentElement.previousElementSibling.querySelector('strong').textContent = Math.round(newWidth) + '%';
            
            // Update color based on usage
            bar.className = bar.className.replace(/bg-(primary|warning|danger)/g, '');
            if (newWidth <= 50) {
                bar.classList.add('bg-primary');
            } else if (newWidth <= 75) {
                bar.classList.add('bg-warning');
            } else {
                bar.classList.add('bg-danger');
            }
        });
    }

    function showAgentDetails(agentName) {
        // Create modal or popup with agent details
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${agentName} - Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Performance Metrics</h6>
                                <ul class="list-unstyled">
                                    <li>Efficiency: ${Math.floor(Math.random() * 20 + 80)}%</li>
                                    <li>Response Time: ${(Math.random() * 2 + 1).toFixed(1)}s</li>
                                    <li>Tasks Today: ${Math.floor(Math.random() * 200 + 50)}</li>
                                    <li>Error Rate: ${(Math.random() * 0.5).toFixed(1)}%</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6>Current Status</h6>
                                <p class="text-success">Online and operational</p>
                                <h6>Last Activity</h6>
                                <p>${new Date().toLocaleTimeString()}</p>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary">Restart Agent</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Clean up modal after closing
        modal.addEventListener('hidden.bs.modal', function() {
            document.body.removeChild(modal);
        });
    }

    // Workflow Visualization
    function initializeWorkflowVisualization() {
        const workflowStages = document.querySelectorAll('.workflow-stage');
        const agentNodes = document.querySelectorAll('.agent-node');
        
        // Add workflow animations
        workflowStages.forEach((stage, index) => {
            setTimeout(() => {
                stage.style.opacity = '0';
                stage.style.transform = 'translateY(20px)';
                stage.style.transition = 'all 0.5s ease';
                
                setTimeout(() => {
                    stage.style.opacity = '1';
                    stage.style.transform = 'translateY(0)';
                }, 100 * index);
            }, 0);
        });
        
        // Agent node interactions
        agentNodes.forEach(node => {
            node.addEventListener('click', function() {
                const agentName = this.querySelector('h6').textContent;
                highlightAgentConnections(this);
                showAgentWorkflow(agentName);
            });
        });
        
        // Update workflow progress
        updateWorkflowProgress();
    }

    function highlightAgentConnections(selectedNode) {
        // Remove previous highlights
        document.querySelectorAll('.agent-node').forEach(node => {
            node.classList.remove('highlighted', 'connected');
        });
        
        // Highlight selected node
        selectedNode.classList.add('highlighted');
        
        // Highlight connected nodes (simulate workflow connections)
        const connections = getAgentConnections(selectedNode);
        connections.forEach(connection => {
            connection.classList.add('connected');
        });
    }

    function getAgentConnections(node) {
        // Simulate agent dependencies
        const agentName = node.querySelector('h6').textContent;
        const allNodes = document.querySelectorAll('.agent-node');
        const connections = [];
        
        // Define some example connections
        const connectionMap = {
            'Document Intelligence': ['Requirements Engineering'],
            'Requirements Engineering': ['Solution Architecture', 'Risk Assessment'],
            'Solution Architecture': ['Project Planning'],
            'Risk Assessment': ['Cost Estimation'],
            'Project Planning': ['Proposal Generation'],
            'Proposal Generation': ['Quality Assurance']
        };
        
        if (connectionMap[agentName]) {
            connectionMap[agentName].forEach(connectedAgent => {
                allNodes.forEach(otherNode => {
                    if (otherNode.querySelector('h6').textContent.includes(connectedAgent)) {
                        connections.push(otherNode);
                    }
                });
            });
        }
        
        return connections;
    }

    function updateWorkflowProgress() {
        const progressBars = document.querySelectorAll('.progress-bar-mini .progress-fill');
        
        progressBars.forEach(bar => {
            const targetWidth = bar.style.width;
            bar.style.width = '0%';
            
            setTimeout(() => {
                bar.style.width = targetWidth;
            }, Math.random() * 1000);
        });
    }

    function showAgentWorkflow(agentName) {
        console.log(`Showing workflow for: ${agentName}`);
        // This would typically show a detailed workflow view
    }

    // Communication Feed
    function initializeCommunicationFeed() {
        const communicationFeed = document.querySelector('.communication-feed');
        if (!communicationFeed) return;
        
        // Auto-scroll to bottom
        communicationFeed.scrollTop = communicationFeed.scrollHeight;
        
        // Simulate new messages
        if (App.realTimeUpdates) {
            setInterval(() => {
                addRandomMessage();
            }, 15000); // New message every 15 seconds
        }
        
        // Message interactions
        const messages = document.querySelectorAll('.message');
        messages.forEach(message => {
            message.addEventListener('click', function() {
                this.classList.toggle('expanded');
            });
        });
    }

    function addRandomMessage() {
        const communicationFeed = document.querySelector('.communication-feed');
        if (!communicationFeed) return;
        
        const messageTemplates = [
            {
                agent: 'Document Intelligence',
                type: 'UPDATE',
                content: 'Processing document page ' + Math.floor(Math.random() * 50 + 1),
                badge: 'bg-info'
            },
            {
                agent: 'Requirements Engineering',
                type: 'QUERY',
                content: 'Clarification needed on requirement REQ-' + Math.floor(Math.random() * 100),
                badge: 'bg-warning'
            },
            {
                agent: 'Agent Orchestrator',
                type: 'NOTIFICATION',
                content: 'Workflow checkpoint reached',
                badge: 'bg-primary'
            }
        ];
        
        const template = messageTemplates[Math.floor(Math.random() * messageTemplates.length)];
        const messageHtml = createMessageHTML(template);
        
        communicationFeed.insertAdjacentHTML('beforeend', messageHtml);
        
        // Auto-scroll to new message
        communicationFeed.scrollTop = communicationFeed.scrollHeight;
        
        // Limit messages to prevent memory issues
        const messages = communicationFeed.querySelectorAll('.message');
        if (messages.length > 20) {
            messages[0].remove();
        }
    }

    function createMessageHTML(template) {
        const timestamp = new Date().toLocaleTimeString();
        return `
            <div class="message-group">
                <div class="message ${template.agent.toLowerCase().includes('orchestrator') ? 'orchestrator' : 'analysis'}">
                    <div class="message-header">
                        <div class="agent-avatar ${template.agent.toLowerCase().includes('orchestrator') ? 'master' : 'analysis'}">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-info">
                            <h6>${template.agent}</h6>
                            <small class="text-muted">${timestamp}</small>
                        </div>
                        <span class="message-type badge ${template.badge}">${template.type}</span>
                    </div>
                    <div class="message-content">
                        <p>${template.content}</p>
                    </div>
                </div>
            </div>
        `;
    }

    // Document Upload
    function initializeDocumentUpload() {
        const uploadArea = document.getElementById('uploadArea');
        if (!uploadArea) return;
        
        // Drag and drop functionality
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
        uploadArea.addEventListener('click', handleUploadClick);
        
        // File input change
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.multiple = true;
        fileInput.accept = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);
        
        fileInput.addEventListener('change', function() {
            handleFiles(this.files);
        });
        
        // Store reference for click handler
        uploadArea.fileInput = fileInput;
    }

    function handleDragOver(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
    }

    function handleDrop(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    }

    function handleUploadClick() {
        this.fileInput.click();
    }

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            if (validateFile(file)) {
                uploadFile(file);
            }
        });
    }

    function validateFile(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        const allowedTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ];
        
        if (file.size > maxSize) {
            showNotification('File too large. Maximum size is 50MB.', 'error');
            return false;
        }
        
        if (!allowedTypes.includes(file.type)) {
            showNotification('File type not supported.', 'error');
            return false;
        }
        
        return true;
    }

    function uploadFile(file) {
        const uploadedFiles = document.querySelector('.uploaded-file').parentElement;
        const fileItem = createFileItem(file);
        
        uploadedFiles.insertAdjacentHTML('afterbegin', fileItem);
        
        // Simulate upload progress
        const newItem = uploadedFiles.firstElementChild;
        const progressBar = newItem.querySelector('.progress-bar');
        const statusBadge = newItem.querySelector('.badge');
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                statusBadge.className = 'badge bg-success';
                statusBadge.innerHTML = '<i class="fas fa-check me-1"></i>Complete';
                showNotification(`File ${file.name} uploaded successfully`, 'success');
            }
            
            if (progressBar) {
                progressBar.style.width = progress + '%';
            }
        }, 200);
    }

    function createFileItem(file) {
        const timestamp = new Date().toLocaleTimeString();
        const fileIcon = getFileIcon(file.type);
        const fileSize = formatFileSize(file.size);
        
        return `
            <div class="uploaded-file">
                <div class="file-icon">
                    <i class="fas ${fileIcon}"></i>
                </div>
                <div class="file-info">
                    <h6>${file.name}</h6>
                    <p class="text-muted small">${fileSize} • Uploaded ${timestamp}</p>
                    <div class="progress" style="height: 4px;">
                        <div class="progress-bar bg-primary" style="width: 0%"></div>
                    </div>
                </div>
                <div class="file-status">
                    <span class="badge bg-warning">
                        <i class="fas fa-spinner fa-spin me-1"></i>Processing
                    </span>
                </div>
                <div class="file-actions">
                    <button class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    function getFileIcon(mimeType) {
        const iconMap = {
            'application/pdf': 'fa-file-pdf text-danger',
            'application/msword': 'fa-file-word text-primary',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'fa-file-word text-primary',
            'application/vnd.ms-excel': 'fa-file-excel text-success',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'fa-file-excel text-success',
            'application/vnd.ms-powerpoint': 'fa-file-powerpoint text-warning',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'fa-file-powerpoint text-warning'
        };
        
        return iconMap[mimeType] || 'fa-file text-secondary';
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Quality Assurance
    function initializeQualityAssurance() {
        const qualityChecks = document.querySelectorAll('.quality-check');
        
        qualityChecks.forEach(check => {
            const header = check.querySelector('.check-header');
            if (header) {
                header.addEventListener('click', function() {
                    const content = check.querySelector('.check-content');
                    if (content) {
                        const isVisible = content.style.display !== 'none';
                        content.style.display = isVisible ? 'none' : 'block';
                        
                        // Add expand/collapse icon
                        const icon = header.querySelector('.check-icon i');
                        if (icon) {
                            icon.className = isVisible ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
                        }
                    }
                });
            }
        });
        
        // Auto-fix functionality
        const autoFixButtons = document.querySelectorAll('[data-action="auto-fix"]');
        autoFixButtons.forEach(button => {
            button.addEventListener('click', function() {
                const check = this.closest('.quality-check');
                simulateAutoFix(check);
            });
        });
    }

    function simulateAutoFix(checkElement) {
        const statusBadge = checkElement.querySelector('.check-status .badge');
        const icon = checkElement.querySelector('.check-icon i');
        
        // Show processing state
        statusBadge.className = 'badge bg-info';
        statusBadge.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Fixing...';
        icon.className = 'fas fa-spinner fa-spin text-info';
        
        // Simulate fix completion
        setTimeout(() => {
            statusBadge.className = 'badge bg-success';
            statusBadge.innerHTML = '<i class="fas fa-check me-1"></i>Fixed';
            icon.className = 'fas fa-check-circle text-success';
            
            checkElement.classList.remove('critical', 'warning');
            checkElement.classList.add('passed');
            
            showNotification('Issue resolved automatically', 'success');
        }, 2000);
    }

    // Notifications
    function initializeNotifications() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notificationContainer')) {
            const container = document.createElement('div');
            container.id = 'notificationContainer';
            container.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 9999;
                max-width: 350px;
            `;
            document.body.appendChild(container);
        }
    }

    function showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notificationContainer');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.style.cssText = 'margin-bottom: 10px; animation: slideInRight 0.3s ease;';
        
        const iconMap = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        
        notification.innerHTML = `
            <i class="fas ${iconMap[type]} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);
    }

    // Real-time Updates
    function initializeRealTimeUpdates() {
        if (!App.realTimeUpdates) return;
        
        // Simulate real-time data updates
        setInterval(() => {
            updateSystemMetrics();
            updateAgentStatuses();
            checkForAlerts();
        }, App.refreshInterval);
        
        // System health check
        setInterval(() => {
            performHealthCheck();
        }, 30000); // Every 30 seconds
    }

    function updateSystemMetrics() {
        // Update dashboard cards
        const metricCards = document.querySelectorAll('.card h3, .card h4');
        metricCards.forEach(metric => {
            if (metric.textContent.match(/^\d+/)) {
                const currentValue = parseInt(metric.textContent);
                const variation = Math.floor((Math.random() - 0.5) * 4); // ±2 variation
                const newValue = Math.max(0, currentValue + variation);
                metric.textContent = metric.textContent.replace(/^\d+/, newValue);
            }
        });
    }

    function checkForAlerts() {
        // Simulate random alerts
        if (Math.random() < 0.05) { // 5% chance
            const alerts = [
                { message: 'High memory usage detected', type: 'warning' },
                { message: 'Agent response time threshold exceeded', type: 'warning' },
                { message: 'New document uploaded for analysis', type: 'info' },
                { message: 'Quality check completed successfully', type: 'success' }
            ];
            
            const alert = alerts[Math.floor(Math.random() * alerts.length)];
            showNotification(alert.message, alert.type);
        }
    }

    function performHealthCheck() {
        console.log('Performing system health check...');
        
        // Update health indicators
        const healthItems = document.querySelectorAll('.health-item .health-status');
        healthItems.forEach(status => {
            // Randomly simulate health issues (very low chance)
            if (Math.random() < 0.02) { // 2% chance of issues
                status.className = 'health-status warning';
                status.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            } else {
                status.className = 'health-status success';
                status.innerHTML = '<i class="fas fa-check-circle"></i>';
            }
        });
    }

    // Utility Functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Export functions for global access
    window.AITenderSystem = {
        showNotification,
        updateAgentStatuses,
        performHealthCheck,
        App
    };

    // Handle page visibility changes
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            App.realTimeUpdates = false;
            console.log('Real-time updates paused (page hidden)');
        } else {
            App.realTimeUpdates = true;
            console.log('Real-time updates resumed (page visible)');
        }
    });

    // Handle window resize
    window.addEventListener('resize', debounce(function() {
        // Adjust layouts for responsive design
        const charts = document.querySelectorAll('canvas');
        charts.forEach(chart => {
            if (chart.chart) {
                chart.chart.resize();
            }
        });
    }, 250));

    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .agent-node.highlighted {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(13, 110, 253, 0.4);
            z-index: 10;
            position: relative;
        }
        
        .agent-node.connected {
            border-color: #198754;
            background: rgba(25, 135, 84, 0.1);
        }
        
        .message.expanded {
            transform: scale(1.02);
            z-index: 5;
            position: relative;
        }
    `;
    document.head.appendChild(style);

})();
