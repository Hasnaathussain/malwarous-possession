// Progressive enhancement for orientation and the hero signal diagram.
(() => {
  const progress = document.querySelector('.reading-progress > span');
  let progressFrame = 0;

  const updateProgress = () => {
    progressFrame = 0;
    if (!progress) return;
    const root = document.documentElement;
    const span = root.scrollHeight - window.innerHeight;
    const value = span > 0 ? Math.min(1, Math.max(0, window.scrollY / span)) : 0;
    progress.style.transform = `scaleX(${value})`;
  };

  const scheduleProgress = () => {
    if (!progressFrame) progressFrame = window.requestAnimationFrame(updateProgress);
  };

  if (progress) {
    window.addEventListener('scroll', scheduleProgress, { passive: true });
    window.addEventListener('resize', scheduleProgress, { passive: true });
    scheduleProgress();
  }

  const signal = document.querySelector('.hero-signal-frame');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

  if (!signal || reducedMotion.matches || !finePointer.matches) return;

  let pointerFrame = 0;
  let shiftX = 0;
  let shiftY = 0;
  let pointerX = 0;
  let pointerY = 0;
  let hasPointer = false;

  const applyPointerShift = () => {
    pointerFrame = 0;
    if (hasPointer && !reducedMotion.matches) {
      const bounds = signal.getBoundingClientRect();
      if (bounds.width && bounds.height) {
        shiftX = Math.max(-5, Math.min(5, ((pointerX - bounds.left) / bounds.width - 0.5) * 10));
        shiftY = Math.max(-4, Math.min(4, ((pointerY - bounds.top) / bounds.height - 0.5) * 8));
      }
    } else {
      shiftX = 0;
      shiftY = 0;
    }
    signal.style.setProperty('--signal-shift-x', `${shiftX}px`);
    signal.style.setProperty('--signal-shift-y', `${shiftY}px`);
  };

  const schedulePointerShift = () => {
    if (!pointerFrame) pointerFrame = window.requestAnimationFrame(applyPointerShift);
  };

  signal.addEventListener('pointermove', event => {
    if (reducedMotion.matches) return;
    pointerX = event.clientX;
    pointerY = event.clientY;
    hasPointer = true;
    schedulePointerShift();
  }, { passive: true });

  signal.addEventListener('pointerleave', () => {
    hasPointer = false;
    schedulePointerShift();
  }, { passive: true });

  reducedMotion.addEventListener?.('change', event => {
    if (!event.matches) return;
    hasPointer = false;
    schedulePointerShift();
  });
})();
