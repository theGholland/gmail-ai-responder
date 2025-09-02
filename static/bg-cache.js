document.addEventListener('DOMContentLoaded', () => {
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

  const gridEl = document.querySelector('.bg-grid');
  if (gridEl) {
    const { vURL, hURL } = makeGridImages();
    gridEl.style.backgroundImage = `url(${vURL}), url(${hURL})`;
    gridEl.style.backgroundSize = '300px 300px, 300px 300px';
  }
});
