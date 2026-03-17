import { createContext, useContext, useState, useEffect } from 'react';

const KEY = 'mp_guide';

export const GuideModeContext = createContext(false);

export function useGuideMode() {
  return useContext(GuideModeContext);
}

export function useGuideModeState() {
  const [guideMode, setGuideMode] = useState(() => {
    try { return localStorage.getItem(KEY) === '1'; }
    catch { return false; }
  });

  function toggle() {
    setGuideMode(v => {
      const next = !v;
      try { localStorage.setItem(KEY, next ? '1' : '0'); } catch {}
      return next;
    });
  }

  return [guideMode, toggle];
}
