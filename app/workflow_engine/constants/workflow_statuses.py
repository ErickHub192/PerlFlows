"""
Workflow Status Constants
Centralized constants for workflow statuses to avoid duplication
"""

class WorkflowStatus:
    """Workflow execution statuses"""
    OAUTH_REQUIRED = "oauth_required"
    NEEDS_USER_INPUT = "needs_user_input"
    WORKFLOW_READY_FOR_REVIEW = "workflow_ready_for_review"
    PENDING_DISCOVERY = "pending_discovery"
    DISCOVERY_NEEDED = "discovery_needed"
    CLARIFICATION_NEEDED = "clarification_needed"
    READY = "ready"
    ERROR = "error"
    COMPLETED = "completed"
    
    # 🚫 DISABLED: New workflow management statuses - NOW HANDLED BY BUTTONS
    # SAVE_WORKFLOW = "save_workflow"
    # ACTIVATE_WORKFLOW = "activate_workflow"
    # EXECUTE_WORKFLOW = "execute_workflow"

class WorkflowStatusGroups:
    """Groups of statuses for different behaviors"""
    
    # Statuses that should skip reflection service
    REFLECTION_SKIP_STATUSES = [
        WorkflowStatus.WORKFLOW_READY_FOR_REVIEW,
        WorkflowStatus.NEEDS_USER_INPUT,
        # WorkflowStatus.SAVE_WORKFLOW,      # DISABLED - HANDLED BY BUTTONS
        # WorkflowStatus.ACTIVATE_WORKFLOW,  # DISABLED - HANDLED BY BUTTONS
        # WorkflowStatus.EXECUTE_WORKFLOW    # DISABLED - HANDLED BY BUTTONS
    ]
    
    # Statuses that are informational and may need CARL translation
    INFORMATIONAL_STATUSES = [
        WorkflowStatus.NEEDS_USER_INPUT,
        WorkflowStatus.WORKFLOW_READY_FOR_REVIEW,
        WorkflowStatus.DISCOVERY_NEEDED,
        # WorkflowStatus.SAVE_WORKFLOW,      # DISABLED - HANDLED BY BUTTONS
        # WorkflowStatus.ACTIVATE_WORKFLOW,  # DISABLED - HANDLED BY BUTTONS
        # WorkflowStatus.EXECUTE_WORKFLOW    # DISABLED - HANDLED BY BUTTONS
    ]
    
    # Statuses that require OAuth
    OAUTH_STATUSES = [
        WorkflowStatus.OAUTH_REQUIRED
    ]
    
    # Statuses that enable frontend workflow review interface
    REVIEW_ENABLED_STATUSES = [
        WorkflowStatus.WORKFLOW_READY_FOR_REVIEW
    ]
    
    # 🚫 DISABLED: Statuses that require ChatWorkflowBridgeService processing - NOW HANDLED BY BUTTONS
    # BRIDGE_SERVICE_STATUSES = [
    #     WorkflowStatus.SAVE_WORKFLOW,
    #     WorkflowStatus.ACTIVATE_WORKFLOW,
    #     WorkflowStatus.EXECUTE_WORKFLOW
    # ]