import { useTemplates, useInstallTemplate } from '../hooks/useMarketplace';

export default function MarketplacePage() {
  const { data: templates = [] } = useTemplates();
  const install = useInstallTemplate();

  return (
    <div className="p-6 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6">Marketplace</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map(t => (
          <div key={t.template_id} className="bg-white p-4 rounded shadow">
            <h2 className="text-lg font-semibold mb-1">{t.name}</h2>
            <p className="text-sm text-gray-500">{t.category}</p>
            <p className="text-gray-700 mb-2 line-clamp-2">{t.description}</p>
            <button
              onClick={() => install.mutate(t.template_id)}
              className="bg-purple hover:bg-purple-hover text-white px-2 py-1 rounded"
            >
              Instalar
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
