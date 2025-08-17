
import WorkflowCard from './WorkflowCard';

/**
 * Lista de workflows.
 * @param {{ flows: Array<{ flow_id: string, name: string, is_active: boolean }> }} props
 */
export default function WorkflowsList({ flows, onDeleteWorkflow }) {
  if (!flows || flows.length === 0) {
    return (
      <div className="text-center p-4 text-gray-500">
        No tienes workflows aún.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {flows.map(flow => (
        <WorkflowCard
          key={flow.flow_id}
          flow={flow}
          onDelete={onDeleteWorkflow}
        />
      ))}
    </div>
  );
}
