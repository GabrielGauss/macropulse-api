export default function StatCard({ label, value, sub, color }) {
  return (
    <div className="card p-4">
      <div className="text-[10px] font-mono uppercase tracking-wide mb-2" style={{ color: 'rgba(255,255,255,0.25)' }}>
        {label}
      </div>
      <div className="text-[22px] font-semibold font-mono leading-none mb-1" style={{ color: color || '#f0f0f0' }}>
        {value}
      </div>
      {sub && (
        <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
          {sub}
        </div>
      )}
    </div>
  );
}
