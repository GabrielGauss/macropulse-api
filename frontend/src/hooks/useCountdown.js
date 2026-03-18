import { useState, useEffect } from 'react';

/**
 * Returns a countdown string "HH:MM:SS" to the next daily 21:00 UTC pipeline run.
 * Updates every second. Returns '' until first tick.
 */
export function useCountdown() {
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    function calc() {
      const now = new Date();
      const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 21, 0, 0));
      if (now >= next) next.setUTCDate(next.getUTCDate() + 1);
      const diff = next - now;
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`);
    }
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, []);

  return countdown;
}
