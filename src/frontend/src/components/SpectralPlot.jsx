import Plot from "react-plotly.js";

export default function SpectralPlot({ wavelengths, reflectance }) {
  if (!wavelengths || !reflectance) return <div>—</div>;
  return (
    <Plot
      data={[{
        x: wavelengths,
        y: reflectance,
        type: "scatter",
        mode: "lines",
        line: { width: 2 },
      }]}
      layout={{
        margin: { l: 60, r: 20, t: 30, b: 50 },
        xaxis: { title: "wavelength (nm)" },
        yaxis: { title: "reflectance |r|²", range: [0, 1] },
        height: 360,
      }}
      style={{ width: "100%" }}
      config={{ responsive: true, displayModeBar: false }}
    />
  );
}
