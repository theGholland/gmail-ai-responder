document.addEventListener('DOMContentLoaded', () => {
  const rootStyles = getComputedStyle(document.documentElement);

  function makeGridImages() {
    const size = 300;
    const color = 'rgba(1,241,248,0.9)';

    const vCanvas = document.createElement('canvas');
    vCanvas.width = size;
    vCanvas.height = size;
    const vCtx = vCanvas.getContext('2d');
    vCtx.fillStyle = color;
    vCtx.fillRect(0, 0, 10, size);
    const vURL = vCanvas.toDataURL();

    const hCanvas = document.createElement('canvas');
    hCanvas.width = size;
    hCanvas.height = size;
    const hCtx = hCanvas.getContext('2d');
    hCtx.fillStyle = color;
    hCtx.fillRect(0, 0, size, 10);
    const hURL = hCanvas.toDataURL();

    return { vURL, hURL };
  }

  function makeSunImage() {
    const size = 512;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d');

    const core = rootStyles.getPropertyValue('--sun-core').trim() || '#ffd29a';
    const rim = rootStyles.getPropertyValue('--sun-rim').trim() || '#ff6a4d';

    const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, '#fff6d2');
    grad.addColorStop(0.38, core);
    grad.addColorStop(0.62, '#ff9c66');
    grad.addColorStop(0.85, rim);
    grad.addColorStop(1, rim);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);

    // build stripe mask and clip with circle
    const mask = document.createElement('canvas');
    mask.width = mask.height = size;
    const mCtx = mask.getContext('2d');
    mCtx.fillStyle = '#000';
    for (let y = 0; y < size; y += 22) {
      mCtx.fillRect(0, y, size, 14);
    }
    mCtx.globalCompositeOperation = 'destination-in';
    mCtx.beginPath();
    mCtx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    mCtx.closePath();
    mCtx.fill();

    ctx.globalCompositeOperation = 'destination-in';
    ctx.drawImage(mask, 0, 0);

    return canvas.toDataURL();
  }

  const gridEl = document.querySelector('.bg-grid');
  if (gridEl) {
    const { vURL, hURL } = makeGridImages();
    gridEl.style.backgroundImage = `url(${vURL}), url(${hURL})`;
    gridEl.style.backgroundSize = '300px 300px, 300px 300px';
  }

  const sunEl = document.querySelector('.bg-sunset');
  if (sunEl) {
    const sunURL = makeSunImage();
    sunEl.style.backgroundImage = `url(${sunURL})`;
    sunEl.style.backgroundRepeat = 'no-repeat';
    sunEl.style.backgroundSize = '100% 100%';
    sunEl.style.webkitMask = 'none';
    sunEl.style.mask = 'none';
  }
});
