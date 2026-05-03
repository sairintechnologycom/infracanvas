import { Search } from 'lucide-react';
import { useViewerStoreOrSingleton } from '../store';

export function SearchBar() {
  const searchQuery = useViewerStoreOrSingleton(s => s.searchQuery);
  const setSearchQuery = useViewerStoreOrSingleton(s => s.setSearchQuery);
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all"
      style={{
        background: 'linear-gradient(135deg, #0f1419 0%, #1a202c 100%)',
        border: '1.5px solid #2d3748',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2), inset 0 1px 2px rgba(255,255,255,0.03)',
      }}>
      <Search size={15} aria-hidden={true} style={{ color: '#64748b', flexShrink: 0 }} />
      <input
        type="text"
        aria-label="Search resources"
        placeholder="Search resources..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="bg-transparent text-sm outline-none placeholder-slate-500 font-medium"
        style={{ color: '#f1f5f9', width: 160 }}
      />
    </div>
  );
}
