import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium transition-all duration-150 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0B0B0D] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer';

  const variants = {
    primary:
      'bg-[#F97316] text-white hover:bg-[#EA580C] active:bg-[#C2410C] focus:ring-[#F97316]/50 shadow-md shadow-[#F97316]/20',
    secondary:
      'bg-[#1E1E21] text-zinc-200 hover:bg-[#27272A] hover:text-white border border-white/10 active:bg-zinc-800 focus:ring-zinc-500/40',
    danger:
      'bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20 active:bg-rose-500/30 focus:ring-rose-500/40',
    ghost:
      'text-zinc-400 hover:text-white hover:bg-white/5 active:bg-white/10 focus:ring-zinc-600/30',
  };

  const sizes = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-sm px-4 py-2.5 gap-2.5 font-semibold',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};
