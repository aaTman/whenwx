import './AnimatedBackground.css';

interface AnimatedBackgroundProps {
  variant?: 'default' | 'cold' | 'warm' | 'storm';
}

export function AnimatedBackground({ variant = 'default' }: AnimatedBackgroundProps) {
  return (
    <div className={`animated-background ${variant}`}>
      <div className="gradient-orb orb-1" />
      <div className="gradient-orb orb-2" />
      <div className="gradient-orb orb-3" />
      <div className="noise-overlay" />
    </div>
  );
}
