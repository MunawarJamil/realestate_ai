import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`relative inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all duration-200 cursor-pointer select-none ${
        isDark
          ? 'bg-[#151517] hover:bg-[#1E1E22] text-zinc-300 hover:text-white border-white/10 hover:border-white/20'
          : 'bg-white hover:bg-[#F4EFE2] text-stone-700 hover:text-stone-900 border-[#E7E0D3] shadow-xs'
      } ${className}`}
      title={isDark ? 'Switch to Light Mode (Porcelain)' : 'Switch to Dark Mode'}
      aria-label="Toggle theme"
    >
      {isDark ? (
        <>
          <Sun className="w-3.5 h-3.5 text-amber-400 transition-transform duration-300 rotate-0 hover:rotate-45" />
          <span className="hidden sm:inline text-[11px]">Light</span>
        </>
      ) : (
        <>
          <Moon className="w-3.5 h-3.5 text-[#F97316] transition-transform duration-300" />
          <span className="hidden sm:inline text-[11px]">Dark</span>
        </>
      )}
    </button>
  );
};
