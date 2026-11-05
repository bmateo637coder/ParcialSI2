/** Quita solo el fondo de color uniforme conectado al borde de la foto.
 * No impone una silueta: conserva mangas, pantalones y detalles interiores.
 * Fotos sobre personas o fondos complejos necesitan corrección manual.
 */
export function removeEdgeBackground(pixels: Uint8ClampedArray, width: number, height: number, tolerance = 32): Uint8ClampedArray {
  const output = new Uint8ClampedArray(pixels);
  if (width < 2 || height < 2 || pixels.length !== width * height * 4) return output;
  const border: number[] = [];
  for (let x = 0; x < width; x++) { border.push(x, (height - 1) * width + x); }
  for (let y = 1; y < height - 1; y++) { border.push(y * width, y * width + width - 1); }
  if (border.filter(i => pixels[i * 4 + 3] < 32).length > border.length * .5) return output;
  const histogram = new Map<number, { count: number; r: number; g: number; b: number }>();
  for (const index of border) {
    const i = index * 4;
    if (pixels[i + 3] < 240) continue;
    const key = (pixels[i] >> 4) * 256 + (pixels[i + 1] >> 4) * 16 + (pixels[i + 2] >> 4);
    const bin = histogram.get(key) ?? { count: 0, r: 0, g: 0, b: 0 };
    bin.count++; bin.r += pixels[i]; bin.g += pixels[i + 1]; bin.b += pixels[i + 2]; histogram.set(key, bin);
  }
  const dominant = [...histogram.values()].sort((a, b) => b.count - a.count)[0];
  if (!dominant || dominant.count < border.length * .25) return output;
  const background = [dominant.r / dominant.count, dominant.g / dominant.count, dominant.b / dominant.count];
  const limit = Math.max(3, Math.min(100, tolerance));
  const visited = new Uint8Array(width * height);
  const queue = new Int32Array(width * height);
  let head = 0; let tail = 0;
  const visit = (index: number) => {
    if (visited[index]) return;
    visited[index] = 1;
    const i = index * 4;
    const distance = Math.sqrt((pixels[i] - background[0]) ** 2 + (pixels[i + 1] - background[1]) ** 2 + (pixels[i + 2] - background[2]) ** 2);
    if (pixels[i + 3] < 16 || distance < limit + 12) {
      output[i + 3] = pixels[i + 3] < 16 ? 0 : Math.round(pixels[i + 3] * Math.max(0, Math.min(1, (distance - limit) / 12)));
      queue[tail++] = index;
    }
  };
  for (const index of border) visit(index);
  while (head < tail) {
    const index = queue[head++]; const x = index % width;
    if (x > 0) visit(index - 1); if (x < width - 1) visit(index + 1);
    if (index >= width) visit(index - width); if (index < width * (height - 1)) visit(index + width);
  }
  // Un fondo casi idéntico a toda la prenda no permite distinguirla de forma segura.
  if (output.filter((v, i) => i % 4 === 3 && v > 30).length < width * height * .015) return new Uint8ClampedArray(pixels);
  return output;
}

export function alphaBounds(pixels: Uint8ClampedArray, width: number, height: number): { x: number; y: number; width: number; height: number } | null {
  let left = width, top = height, right = -1, bottom = -1;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) if (pixels[(y * width + x) * 4 + 3] > 16) {
    left = Math.min(left, x); right = Math.max(right, x); top = Math.min(top, y); bottom = Math.max(bottom, y);
  }
  if (right < left) return null;
  const padding = 3;
  left = Math.max(0, left - padding); top = Math.max(0, top - padding);
  right = Math.min(width - 1, right + padding); bottom = Math.min(height - 1, bottom + padding);
  return { x: left, y: top, width: right - left + 1, height: bottom - top + 1 };
}

/** Geometría compartida por video, seguimiento corporal y captura. */
export function coverGeometry(sourceWidth: number, sourceHeight: number, width: number, height: number) {
  const scale = Math.max(width / sourceWidth, height / sourceHeight);
  return { scale, x: (width - sourceWidth * scale) / 2, y: (height - sourceHeight * scale) / 2 };
}
