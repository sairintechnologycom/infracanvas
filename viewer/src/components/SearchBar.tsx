import { Search } from 'lucide-react';
import { useStore } from '../store';

export function SearchBar() {
  const searchQuery = useStore(s => s.searchQuery);
  const setSearchQuery = useStore(s => s.setSearchQuery);
  return (
    <div className="flex items-center gap-1 px-2 py-1 rounded"
      style={{ background: '#111827', border: '1px solid #1e293b' }}>
      <Search size={14} aria-hidden={true} style={{ color: '#64748b' }} />
      <input
        type="text"
        aria-label="Search resources"
        placeholder="Search resources..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="bg-transparent text-xs outline-none"
        style={{ color: '#e2e8f0', width: 140 }}
      />
    </div>
  );
}
