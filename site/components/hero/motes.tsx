"use client";
// Hextech motes with wispy tails drifting up through the hero (A37). Off
// under reduced motion; paused by the browser when the tab is hidden.
import { useEffect, useRef } from "react";

type Mote = { x: number; y: number; vx: number; vy: number; ph: number; r: number; life: number; max: number; trail: [number, number][] };

export function Motes() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = c.getContext("2d")!;
    const band = c.parentElement!;
    let w = 0, h = 0, raf = 0;
    const fit = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      w = band.clientWidth; h = band.clientHeight;
      c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    fit();
    const ro = new ResizeObserver(fit); ro.observe(band);
    const spawn = (fresh: boolean): Mote => ({ x: Math.random() * w, y: fresh ? Math.random() * h : h + 10, vy: -(0.25 + Math.random() * 0.6),
      vx: 0.1 + Math.random() * 0.35, ph: Math.random() * 6.28, r: 0.6 + Math.random() * 1.6, life: 0, max: 380 + Math.random() * 520, trail: [] });
    const motes = Array.from({ length: 70 }, () => spawn(true));
    const tick = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.globalCompositeOperation = "lighter";
      for (const m of motes) {
        m.life++; m.ph += 0.02; m.x += m.vx + Math.sin(m.ph) * 0.35; m.y += m.vy;
        m.trail.push([m.x, m.y]); if (m.trail.length > 14) m.trail.shift();
        const a = Math.sin(Math.PI * Math.min(1, m.life / m.max)) * 0.9;
        for (let k = 1; k < m.trail.length; k++) {
          ctx.strokeStyle = `rgba(10,200,185,${((a * k) / m.trail.length * 0.5).toFixed(3)})`;
          ctx.lineWidth = (m.r * k) / m.trail.length * 1.4;
          ctx.beginPath(); ctx.moveTo(...m.trail[k - 1]); ctx.lineTo(...m.trail[k]); ctx.stroke();
        }
        const g = ctx.createRadialGradient(m.x, m.y, 0, m.x, m.y, m.r * 5);
        g.addColorStop(0, `rgba(205,250,250,${a.toFixed(3)})`); g.addColorStop(1, "rgba(10,200,185,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(m.x, m.y, m.r * 5, 0, 6.283); ctx.fill();
        if (m.life > m.max || m.y < -20 || m.x > w + 20) Object.assign(m, spawn(false));
      }
      ctx.globalCompositeOperation = "source-over";
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, []);
  return <canvas id="motes" ref={ref} aria-hidden="true" />;
}
