const TIER_CONFIG = {
  free:    { color: 'bg-gray-100 text-gray-600 border border-gray-200', label: 'Free' },
  starter: { color: 'bg-blue-100 text-blue-700 border border-blue-200', label: 'Starter' },
  pro:     { color: 'bg-purple-100 text-purple-700 border border-purple-200', label: 'Pro' },
  owner:   { color: 'bg-amber-100 text-amber-700 border border-amber-200', label: 'Owner' },
};

export function TierBadge({ tier = 'free', className = '' }) {
  const config = TIER_CONFIG[tier] ?? TIER_CONFIG.free;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.color} ${className}`}>
      {config.label}
    </span>
  );
}
