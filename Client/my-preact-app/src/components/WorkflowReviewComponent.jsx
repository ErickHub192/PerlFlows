// src/components/WorkflowReviewComponent.jsx

import { useState } from 'preact/hooks';

export default function WorkflowReviewComponent({ 
  workflowData, 
  onSave, 
  onClose,
  isModifying = false,
  chatId,
  onWorkflowDecision
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!workflowData) return null;

  const steps = workflowData.steps || [];
  const metadata = workflowData.metadata || {};
  const workflowSummary = metadata.workflow_summary || workflowData.workflow_summary || {};

  return (
    <div className="workflow-review-container">
      <div className="workflow-review-header">
        <div className="review-title">
          <h3>🔍 Workflow Review</h3>
          <span className="review-subtitle">
            {steps.length} pasos • {metadata.workflow_type || 'classic'} workflow
          </span>
        </div>
        <div className="review-controls">
          <button 
            className="btn-expand"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? '▼' : '▶'}
          </button>
          <button 
            className="btn-close" 
            onClick={onClose}
          >
            ✕
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="workflow-review-content">
          {isModifying && (
            <div className="modifying-indicator">
              <span className="spinner">⟳</span>
              Modificando workflow...
            </div>
          )}

          {/* Workflow Summary Section */}
          {workflowSummary.title && (
            <div className="workflow-summary">
              <div className="summary-header">
                <h4 className="workflow-title">🎯 {workflowSummary.title}</h4>
                {workflowSummary.estimated_time && (
                  <span className="estimated-time">⏱️ {workflowSummary.estimated_time}</span>
                )}
              </div>
              
              {workflowSummary.description && (
                <p className="workflow-description">{workflowSummary.description}</p>
              )}
              
              {workflowSummary.trigger && (
                <div className="workflow-trigger">
                  <strong>🚀 Disparador:</strong> {workflowSummary.trigger}
                </div>
              )}
              
              {workflowSummary.actions && workflowSummary.actions.length > 0 && (
                <div className="workflow-actions-summary">
                  <strong>⚡ Acciones:</strong>
                  <ul>
                    {workflowSummary.actions.map((action, idx) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div className="workflow-steps">
            {steps.map((step, index) => (
              <div key={step.id || index} className="workflow-step">
                <div className="step-header">
                  <span className="step-number">{index + 1}</span>
                  <span className="step-connector">{step.connector}</span>
                  <span className="step-action">{step.action}</span>
                </div>
                
                {step.description && (
                  <div className="step-description">
                    {step.description}
                  </div>
                )}

                {step.parameters && Object.keys(step.parameters).length > 0 && (
                  <div className="step-parameters">
                    <summary className="params-toggle">Parámetros</summary>
                    <div className="params-list">
                      {Object.entries(step.parameters).map(([key, value]) => (
                        <div key={key} className="param-item">
                          <span className="param-key">{key}:</span>
                          <span className="param-value">
                            {typeof value === 'string' && value.startsWith('{{') 
                              ? <em className="template-var">{value}</em>
                              : JSON.stringify(value)
                            }
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="workflow-review-footer">
            <div className="review-info">
              {metadata.confidence && (
                <span className="confidence">
                  Confianza: {Math.round(metadata.confidence * 100)}%
                </span>
              )}
              {metadata.modified && (
                <span className="modified-badge">Modificado</span>
              )}
            </div>
            
            <div className="review-actions">
              {onWorkflowDecision ? (
                // Nueva funcionalidad - usar Bridge Service
                <>
                  <button 
                    className="btn-save-workflow"
                    onClick={() => onWorkflowDecision('save')}
                    disabled={isModifying}
                  >
                    💾 Guardar
                  </button>
                  <button 
                    className="btn-activate-workflow"
                    onClick={() => onWorkflowDecision('activate')}
                    disabled={isModifying}
                  >
                    🔄 Activar
                  </button>
                  <button 
                    className="btn-execute-workflow"
                    onClick={() => onWorkflowDecision('execute')}
                    disabled={isModifying}
                  >
                    ⚡ Ejecutar
                  </button>
                </>
              ) : (
                // Funcionalidad legacy - backwards compatibility
                <button 
                  className="btn-save-workflow"
                  onClick={onSave}
                  disabled={isModifying}
                >
                  💾 Guardar Workflow
                </button>
              )}
            </div>
          </div>

          <div className="review-instructions">
            <p>💬 <strong>Puedes modificar este workflow:</strong></p>
            <ul>
              <li>"Cambia la hora a 8am"</li>
              <li>"Agrega envío por email"</li>
              <li>"Quita el paso de validación"</li>
            </ul>
          </div>
        </div>
      )}

      <style jsx>{`
        .workflow-review-container {
          background: #f8f9fa;
          border: 2px solid #e9ecef;
          border-radius: 12px;
          margin: 16px 0;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .workflow-review-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border-radius: 10px 10px 0 0;
        }

        .review-title h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .review-subtitle {
          font-size: 14px;
          opacity: 0.9;
          margin-top: 4px;
          display: block;
        }

        .review-controls {
          display: flex;
          gap: 8px;
        }

        .btn-expand, .btn-close {
          background: rgba(255,255,255,0.2);
          border: none;
          color: white;
          padding: 8px 12px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
        }

        .btn-expand:hover, .btn-close:hover {
          background: rgba(255,255,255,0.3);
        }

        .workflow-review-content {
          padding: 20px;
        }

        .workflow-summary {
          background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
          border: 1px solid #e0e6ff;
          border-radius: 8px;
          margin: 0 0 20px 0;
          padding: 20px;
        }

        .summary-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .workflow-title {
          margin: 0;
          font-size: 20px;
          font-weight: 700;
          color: #4a5568;
        }

        .estimated-time {
          background: #f0f4ff;
          color: #5a67d8;
          padding: 4px 12px;
          border-radius: 16px;
          font-size: 13px;
          font-weight: 500;
        }

        .workflow-description {
          font-size: 16px;
          line-height: 1.6;
          color: #2d3748;
          margin: 12px 0;
          background: white;
          padding: 16px;
          border-radius: 6px;
          border-left: 4px solid #667eea;
        }

        .workflow-trigger {
          background: #f0fff4;
          border: 1px solid #9ae6b4;
          border-radius: 6px;
          padding: 12px;
          margin: 12px 0;
          color: #2f855a;
        }

        .workflow-actions-summary {
          margin-top: 16px;
        }

        .workflow-actions-summary strong {
          color: #4a5568;
          font-size: 15px;
        }

        .workflow-actions-summary ul {
          margin: 8px 0 0 0;
          padding-left: 20px;
          list-style: none;
        }

        .workflow-actions-summary li {
          margin: 6px 0;
          color: #2d3748;
          position: relative;
        }

        .workflow-actions-summary li:before {
          content: "⚡";
          position: absolute;
          left: -18px;
        }

        .modifying-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          background: #fff3cd;
          color: #856404;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 16px;
        }

        .spinner {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .workflow-steps {
          margin-bottom: 20px;
        }

        .workflow-step {
          background: white;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
        }

        .step-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 8px;
        }

        .step-number {
          background: #667eea;
          color: white;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: bold;
        }

        .step-connector {
          background: #e9ecef;
          color: #495057;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        .step-action {
          color: #495057;
          font-weight: 500;
        }

        .step-description {
          color: #6c757d;
          font-size: 14px;
          margin-bottom: 8px;
        }

        .step-parameters {
          margin-top: 12px;
        }

        .params-toggle {
          color: #667eea;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          margin-bottom: 8px;
          display: block;
        }

        .params-list {
          background: #f8f9fa;
          border-radius: 4px;
          padding: 8px;
        }

        .param-item {
          display: flex;
          gap: 8px;
          margin-bottom: 4px;
          font-size: 12px;
        }

        .param-key {
          color: #495057;
          font-weight: 500;
          min-width: 80px;
        }

        .param-value {
          color: #6c757d;
          font-family: monospace;
        }

        .template-var {
          color: #667eea;
          font-style: italic;
        }

        .workflow-review-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 16px;
          border-top: 1px solid #e9ecef;
        }

        .review-info {
          display: flex;
          gap: 12px;
          align-items: center;
        }

        .confidence {
          background: #d4edda;
          color: #155724;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        .modified-badge {
          background: #ffeaa7;
          color: #d68910;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        .review-actions {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .btn-save-workflow,
        .btn-activate-workflow,
        .btn-execute-workflow {
          border: none;
          padding: 12px 20px;
          border-radius: 8px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          color: white;
          font-size: 14px;
          flex: 1;
          min-width: 120px;
        }

        .btn-save-workflow {
          background: linear-gradient(135deg, #00b894, #00a085);
        }

        .btn-activate-workflow {
          background: linear-gradient(135deg, #0984e3, #0773c5);
        }

        .btn-execute-workflow {
          background: linear-gradient(135deg, #fd79a8, #e84393);
        }

        .btn-save-workflow:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0,184,148,0.3);
        }

        .btn-activate-workflow:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(9,132,227,0.3);
        }

        .btn-execute-workflow:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(253,121,168,0.3);
        }

        .btn-save-workflow:disabled,
        .btn-activate-workflow:disabled,
        .btn-execute-workflow:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .review-instructions {
          margin-top: 16px;
          background: #e7f3ff;
          padding: 16px;
          border-radius: 8px;
          border-left: 4px solid #667eea;
        }

        .review-instructions p {
          margin: 0 0 8px 0;
          color: #495057;
          font-size: 14px;
        }

        .review-instructions ul {
          margin: 0;
          padding-left: 20px;
          color: #6c757d;
          font-size: 13px;
        }

        .review-instructions li {
          margin-bottom: 4px;
        }
      `}</style>
    </div>
  );
}