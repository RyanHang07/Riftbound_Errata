"use client";
// The thesis in five seconds (A35): one question, two right answers, by date.
// Paraphrase only; the refs are numbers. Pausable; with reduced motion it
// flips only on the button and does not tilt.
import { useEffect, useRef, useState } from "react";
import { CardDressing, clock } from "./wisp";

export function FlipCard() {
  const [flipped, setFlipped] = useState(false);
  const [playing, setPlaying] = useState(true);
  const [still, setStill] = useState(false);
  const tilt = useRef<HTMLDivElement>(null);

  useEffect(() => setStill(matchMedia("(prefers-reduced-motion: reduce)").matches), []);
  useEffect(() => {
    if (still || !playing) return;
    const t = setInterval(() => setFlipped((f) => !f), 4500);
    return () => clearInterval(t);
  }, [playing, still]);

  const move = (e: React.PointerEvent) => {
    const el = tilt.current;
    if (still || !el) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `rotateX(${(-y * 10).toFixed(2)}deg) rotateY(${(x * 12).toFixed(2)}deg)`;
  };

  return (
    <div className="flip-wrap">
      <div className="flip-tilt" ref={tilt} onPointerMove={move} onPointerLeave={() => tilt.current && (tilt.current.style.transform = "")}>
        <div className={`flip${flipped ? " flipped" : ""}`} aria-live="polite">
          <div className="flip-face front" style={clock(3)}>
            <div className="in">
              <span className="status">Outdated after 24 Jul 2026</span>
              <div className="ver">Core Rules v1.3<span>in force 30 Mar to 24 Jul 2026</span></div>
              <div className="claim"><b>No.</b>A countered spell was not played at all, so it could not turn on Legion.</div>
              <div className="ref">core@1.3:419.4.b</div>
            </div>
            <CardDressing i={3} />
          </div>
          <div className="flip-face back" style={clock(7)}>
            <div className="in">
              <span className="status">In force today</span>
              <div className="ver">Core Rules v1.4<span>in force since 24 Jul 2026</span></div>
              <div className="claim"><b>Yes.</b>Play triggers still don&apos;t fire, but a check for &ldquo;played&rdquo; now looks at whether the card was <mark>Finalized</mark>. Legion turns on.</div>
              <div className="ref">core@1.4:419.4.a.1</div>
            </div>
            <CardDressing i={7} />
          </div>
        </div>
      </div>
      <div className="flip-caption">
        &ldquo;If my spell gets countered, does it still count for Legion?&rdquo; The same question, two right answers, depending on the date.
        <br />
        <button type="button" onClick={() => (still ? setFlipped((f) => !f) : setPlaying((p) => !p))}>
          {still ? "Flip" : playing ? "Pause" : "Play"}
        </button>
      </div>
    </div>
  );
}
