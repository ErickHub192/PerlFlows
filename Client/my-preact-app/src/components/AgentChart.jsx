import { useState } from 'preact/hooks';

export default function AgentChart({ analytics }) {
  const [chartType, setChartType] = useState('success');

  if (!analytics || !analytics.daily_stats) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-gray-500">No hay datos de análisis disponibles</div>
      </div>
    );
  }

  const { daily_stats, statistics } = analytics;

  // Prepare data for charts
  const maxRuns = Math.max(...daily_stats.map(d => d.total_runs), 1);
  const maxSuccessRate = 100;

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      month: 'short',
      day: 'numeric'
    });
  };

  const renderBarChart = (data, maxValue, getValue, color) => {
    return (
      <div className="flex items-end justify-between h-48 px-2 py-4 bg-gray-50">
        {data.map((item, index) => {
          const value = getValue(item);
          const height = maxValue > 0 ? (value / maxValue) * 100 : 0;
          
          return (
            <div key={index} className="flex flex-col items-center flex-1 max-w-12">
              <div 
                className={`w-full ${color} rounded-t transition-all duration-300 hover:opacity-80`}
                style={{ height: `${height}%`, minHeight: value > 0 ? '4px' : '0px' }}
                title={`${formatDate(item.date)}: ${value}`}
              />
              <div className="text-xs text-gray-500 mt-2 text-center">
                {formatDate(item.date)}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Chart Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Análisis de Rendimiento</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setChartType('success')}
              className={`px-3 py-1 rounded text-sm ${
                chartType === 'success' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Tasa de Éxito
            </button>
            <button
              onClick={() => setChartType('runs')}
              className={`px-3 py-1 rounded text-sm ${
                chartType === 'runs' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Volumen
            </button>
          </div>
        </div>

        {/* Chart */}
        <div className="relative">
          {chartType === 'success' ? (
            <div>
              <div className="text-sm text-gray-600 mb-2">Tasa de Éxito Diaria (%)</div>
              {renderBarChart(
                daily_stats,
                maxSuccessRate,
                (item) => item.success_rate || 0,
                'bg-green-500'
              )}
            </div>
          ) : (
            <div>
              <div className="text-sm text-gray-600 mb-2">Ejecuciones Diarias</div>
              {renderBarChart(
                daily_stats,
                maxRuns,
                (item) => item.total_runs,
                'bg-blue-500'
              )}
            </div>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Success/Failure Breakdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="text-md font-semibold mb-4">Distribución de Resultados</h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Exitosas</span>
              <div className="flex items-center gap-2">
                <div className="w-20 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full"
                    style={{ 
                      width: `${statistics.total_runs > 0 ? (statistics.successful_runs / statistics.total_runs) * 100 : 0}%`
                    }}
                  />
                </div>
                <span className="text-sm font-medium">{statistics.successful_runs}</span>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Fallidas</span>
              <div className="flex items-center gap-2">
                <div className="w-20 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-red-500 h-2 rounded-full"
                    style={{ 
                      width: `${statistics.total_runs > 0 ? (statistics.failed_runs / statistics.total_runs) * 100 : 0}%`
                    }}
                  />
                </div>
                <span className="text-sm font-medium">{statistics.failed_runs}</span>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">En Ejecución</span>
              <div className="flex items-center gap-2">
                <div className="w-20 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ 
                      width: `${statistics.total_runs > 0 ? (statistics.running_runs / statistics.total_runs) * 100 : 0}%`
                    }}
                  />
                </div>
                <span className="text-sm font-medium">{statistics.running_runs}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="text-md font-semibold mb-4">Métricas de Rendimiento</h4>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Duración Promedio</span>
              <span className="text-sm font-medium">
                {statistics.average_duration_minutes?.toFixed(1) || 0} minutos
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Última Ejecución</span>
              <span className="text-sm font-medium">
                {statistics.last_run_date 
                  ? new Date(statistics.last_run_date).toLocaleDateString('es-ES')
                  : 'Nunca'
                }
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Total Ejecutado</span>
              <span className="text-sm font-medium">{statistics.total_runs}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">En Cola</span>
              <span className="text-sm font-medium">{statistics.queued_runs}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Period Info */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm text-gray-500 text-center">
          Período analizado: {new Date(analytics.period_start).toLocaleDateString('es-ES')} - {new Date(analytics.period_end).toLocaleDateString('es-ES')}
        </div>
      </div>
    </div>
  );
}