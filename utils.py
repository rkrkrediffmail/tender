def consolidate_project_key_points(project_id):
    """Consolidate all key points for a project"""
    # Get all key points for the project
    all_key_points = KeyPoint.query.filter_by(project_id=project_id).all()

    if len(all_key_points) == 0:
        return

    # Convert to dict format for AI processing
    key_points_data = []
    for kp in all_key_points:
        key_points_data.append({
            'id': kp.id,
            'document_id': kp.document_id,
            'content': kp.content,
            'type': kp.type,
            'priority': kp.priority,
            'page': kp.page,
            'section': kp.section,
            'confidence': float(kp.confidence) if kp.confidence else 0.8,
            'tags': kp.tags
        })

    # Get document processor instance
    from main import app
    with app.app_context():
        doc_processor = app.config['DOCUMENT_PROCESSOR']

        # Consolidate using AI
        consolidated_points = doc_processor.consolidate_key_points(key_points_data)

        # Clear existing consolidated points
        ConsolidatedKeyPoint.query.filter_by(project_id=project_id).delete()

        # Save new consolidated points
        for cp_data in consolidated_points:
            consolidated_point = ConsolidatedKeyPoint(
                project_id=project_id,
                content=cp_data['content'],
                type=cp_data['type'],
                priority=cp_data['priority'],
                source_document_ids=cp_data.get('source_document_ids', []),
                source_key_point_ids=cp_data.get('source_key_point_ids', []),
                final_decision=cp_data.get('final_decision', ''),
                reasoning=cp_data.get('reasoning', ''),
                confidence=cp_data.get('confidence', 0.8)
            )
            db.session.add(consolidated_point)

        # Mark original key points as consolidated
        consolidated_kp_ids = []
        for cp_data in consolidated_points:
            consolidated_kp_ids.extend(cp_data.get('source_key_point_ids', []))

        if consolidated_kp_ids:
            KeyPoint.query.filter(KeyPoint.id.in_(consolidated_kp_ids))\
                         .update({KeyPoint.is_consolidated: True}, synchronize_session=False)

        db.session.commit()

def detect_project_conflicts(project_id):
    """Detect conflicts in project key points"""
    # Get all key points for conflict detection
    all_key_points = KeyPoint.query.filter_by(project_id=project_id).all()

    if len(all_key_points) < 2:
        return

    # Convert to dict format
    key_points_data = []
    for kp in all_key_points:
        key_points_data.append({
            'id': kp.id,
            'document_id': kp.document_id,
            'content': kp.content,
            'type': kp.type,
            'priority': kp.priority,
            'page': kp.page,
            'section': kp.section
        })

    from main import app
    with app.app_context():
        doc_processor = app.config['DOCUMENT_PROCESSOR']

        # Detect conflicts using AI
        detected_conflicts = doc_processor.detect_conflicts(key_points_data)

        # Clear existing conflicts
        Conflict.query.filter_by(project_id=project_id).delete()

        # Save new conflicts
        for conflict_data in detected_conflicts:
            conflict = Conflict(
                project_id=project_id,
                conflict_type=conflict_data['conflict_type'],
                description=conflict_data['description'],
                conflicting_key_point_ids=conflict_data.get('conflicting_key_point_ids', []),
                resolution_strategy=conflict_data.get('resolution_strategy', ''),
                resolution_reasoning=conflict_data.get('resolution_reasoning', ''),
                status='pending'
            )
            db.session.add(conflict)

        db.session.commit()

def identify_project_missing_info(project_id):
    """Identify missing information for a project"""
    # Get consolidated key points
    consolidated_points = ConsolidatedKeyPoint.query.filter_by(project_id=project_id).all()

    # Convert to dict format
    points_data = []
    for cp in consolidated_points:
        points_data.append({
            'content': cp.content,
            'type': cp.type,
            'priority': cp.priority,
            'confidence': float(cp.confidence) if cp.confidence else 0.8
        })

    from main import app
    with app.app_context():
        doc_processor = app.config['DOCUMENT_PROCESSOR']

        # Identify missing information using AI
        missing_items = doc_processor.identify_missing_information(points_data)

        # Clear existing missing information
        MissingInformation.query.filter_by(project_id=project_id).delete()

        # Save new missing information
        for item_data in missing_items:
            missing_info = MissingInformation(
                project_id=project_id,
                category=item_data['category'],
                description=item_data['description'],
                importance=item_data['importance'],
                suggested_questions=item_data.get('suggested_questions', []),
                status='pending'
            )
            db.session.add(missing_info)

        db.session.commit()

def generate_project_markdown_report(project_id):
    """Generate comprehensive markdown report for a project"""
    project = Project.query.get_or_404(project_id)
    documents = RFPDocument.query.filter_by(project_id=project_id).all()
    consolidated_points = ConsolidatedKeyPoint.query.filter_by(project_id=project_id).all()
    conflicts = Conflict.query.filter_by(project_id=project_id).all()
    missing_info = MissingInformation.query.filter_by(project_id=project_id).all()

    markdown = f"""# RFP Analysis Report: {project.name}

**Project ID:** {project.id}
**Client:** {project.client_name or 'Not specified'}
**Created:** {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
**Status:** {project.status.title()}

## Executive Summary

- **Documents Processed:** {len(documents)}
- **Key Points Identified:** {len(consolidated_points)}
- **Conflicts Detected:** {len([c for c in conflicts if c.status == 'pending'])}
- **Missing Information Items:** {len([m for m in missing_info if m.status == 'pending'])}

## Document Overview

"""

    for doc in documents:
        markdown += f"""### {doc.original_name}
- **Type:** {doc.document_type.replace('_', ' ').title()}
- **Size:** {doc.file_size / 1024:.1f} KB
- **Pages:** {doc.page_count or 'Unknown'}
- **Status:** {doc.processing_status.title()}
- **Uploaded:** {doc.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}

"""

    # Group consolidated points by type
    points_by_type = {}
    for point in consolidated_points:
        if point.type not in points_by_type:
            points_by_type[point.type] = []
        points_by_type[point.type].append(point)

    markdown += "## Consolidated Key Points\n\n"

    for point_type, points in points_by_type.items():
        markdown += f"### {point_type.replace('_', ' ').title()}\n\n"

        # Sort by priority
        priority_order = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
        points.sort(key=lambda x: priority_order.get(x.priority, 5))

        for point in points:
            markdown += f"""#### {point.priority.title()} Priority
**Content:** {point.content}

**Final Decision:** {point.final_decision or 'No specific decision recorded'}

**Reasoning:** {point.reasoning or 'No reasoning provided'}

**Sources:** {len(point.source_document_ids)} document(s)

**Confidence:** {float(point.confidence) if point.confidence else 'N/A'}

---

"""

    if conflicts:
        markdown += "## Detected Conflicts\n\n"

        for conflict in conflicts:
            status_icon = "🔴" if conflict.status == 'pending' else "🟢"
            markdown += f"""### {status_icon} {conflict.conflict_type.replace('_', ' ').title()} Conflict

**Description:** {conflict.description}

**Resolution Strategy:** {conflict.resolution_strategy or 'Not determined'}

**Reasoning:** {conflict.resolution_reasoning or 'No reasoning provided'}

**Status:** {conflict.status.title()}

**Conflicting Points:** {len(conflict.conflicting_key_point_ids)} key points involved

---

"""

    if missing_info:
        markdown += "## Missing Information\n\n"

        # Group by importance
        info_by_importance = {}
        for info in missing_info:
            if info.importance not in info_by_importance:
                info_by_importance[info.importance] = []
            info_by_importance[info.importance].append(info)

        importance_order = ['critical', 'high', 'medium', 'low']

        for importance in importance_order:
            if importance in info_by_importance:
                icon = "🚨" if importance == 'critical' else "⚠️" if importance == 'high' else "ℹ️"
                markdown += f"### {icon} {importance.title()} Importance\n\n"

                for info in info_by_importance[importance]:
                    markdown += f"""#### {info.category.replace('_', ' ').title()}

**Missing:** {info.description}

**Suggested Questions:**
"""
                    for question in info.suggested_questions:
                        markdown += f"- {question}\n"

                    markdown += "\n---\n\n"

    markdown += f"""## Report Generation Details

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**System:** AI-Powered Tender Analysis System
**Analysis Engine:** Claude Sonnet 4

---

*This report was automatically generated by analyzing {len(documents)} RFP documents using advanced AI processing. Please review all findings and seek clarification on identified conflicts and missing information.*
"""

    return markdown
