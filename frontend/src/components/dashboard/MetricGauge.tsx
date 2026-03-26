interface Props {
  value: number;
  label: string;
  size?: number;
  color?: string;
}

export default function MetricGauge({ value, label, size = 100, color = '#3b82f6' }: Props) {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(value, 100) / 100) * circumference;

  const getColor = () => {
    if (value > 90) return '#ef4444';
    if (value > 70) return '#f59e0b';
    return color;
  };

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1f2937"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold text-gray-100">{Math.round(value)}%</span>
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</span>
      </div>
    </div>
  );
}
