// Ornaments and blue energy wisps for a card (A37). Each card gets its own
// clock from its index so the energy never pulses in unison.
export function CardDressing({ i }: { i: number }) {
  return (
    <>
      <span className="orn t" />
      <span className="orn b" />
      <svg className="wisp" viewBox="0 0 100 140" preserveAspectRatio="none" aria-hidden="true">
        <path pathLength={100} className="w1" d="M7 0H93L100 7V133L93 140H7L0 133V7Z" />
        <path pathLength={100} className="w2" d="M7 0H93L100 7V133L93 140H7L0 133V7Z" />
      </svg>
    </>
  );
}

export const clock = (i: number) =>
  ({ "--wd": `${(5.5 + ((i * 1.37) % 4)).toFixed(2)}s`, "--wdl": `${(-((i * 2.11) % 7)).toFixed(2)}s` }) as React.CSSProperties;
