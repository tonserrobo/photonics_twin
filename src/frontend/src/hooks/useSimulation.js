import { useEffect, useRef, useState } from "react";

const DEBOUNCE_MS = 30;

export function useSimulation(params, sweep, component = "bragg_grating") {
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("connecting"); // connecting | live | error
  const [error,  setError]  = useState(null);
  const wsRef    = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/sim?component=${component}`);
    wsRef.current = ws;
    ws.onopen  = () => setStatus("live");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "error") { setError(msg); }
      else                        { setError(null); setResult(msg); }
    };
    return () => ws.close();
  }, [component]);

  useEffect(() => {
    if (status !== "live") return;
    if (!params || !sweep) return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      wsRef.current.send(JSON.stringify({ type: "simulate", params, sweep }));
    }, DEBOUNCE_MS);
  }, [params, sweep, status]);

  return { result, status, error };
}
