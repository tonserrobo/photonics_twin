export default function LayerStackView({ stack }) {
  if (!stack || stack.length === 0) return <div>—</div>;

  const total = stack.reduce((s, L) => s + L.thickness_nm, 0);
  const nMin = Math.min(...stack.map((L) => L.n_at_centre));
  const nMax = Math.max(...stack.map((L) => L.n_at_centre));
  const greyscale = (n) => {
    const t = nMax === nMin ? 0.5 : (n - nMin) / (nMax - nMin);
    const v = Math.round(220 - 180 * t); // low n → light, high n → dark
    return `rgb(${v},${v},${v})`;
  };

  const W = 800, H = 80;
  let x = 0;
  return (
    <div>
      <h3>Layer stack ({stack.length} layers, total {total.toFixed(0)} nm)</h3>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ border: "1px solid #ccc" }}>
        {stack.map((L) => {
          const w = (L.thickness_nm / total) * W;
          const rect = (
            <g key={L.index}>
              <rect x={x} y={0} width={w} height={H}
                    fill={greyscale(L.n_at_centre)} stroke="#666" strokeWidth="0.5" />
              <title>{`${L.material} — ${L.thickness_nm.toFixed(2)} nm — n=${L.n_at_centre.toFixed(3)}`}</title>
            </g>
          );
          x += w;
          return rect;
        })}
      </svg>
    </div>
  );
}
