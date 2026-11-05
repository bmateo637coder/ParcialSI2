import 'dart:math' as math;
import 'dart:typed_data';

({int left, int top, int width, int height})? garmentAlphaBounds(
  Uint8List pixels,
  int width,
  int height,
) {
  var left = width, top = height, right = -1, bottom = -1;
  for (var y = 0; y < height; y++) {
    for (var x = 0; x < width; x++) {
      if (pixels[(y * width + x) * 4 + 3] > 16) {
        left = math.min(left, x);
        right = math.max(right, x);
        top = math.min(top, y);
        bottom = math.max(bottom, y);
      }
    }
  }
  if (right < left) return null;
  left = math.max(0, left - 3);
  top = math.max(0, top - 3);
  right = math.min(width - 1, right + 3);
  bottom = math.min(height - 1, bottom + 3);
  return (
    left: left,
    top: top,
    width: right - left + 1,
    height: bottom - top + 1,
  );
}

/// Elimina únicamente el fondo uniforme conectado al borde. Conserva el alfa
/// existente y los detalles claros encerrados dentro de la prenda.
Uint8List removeGarmentBackground(
  Uint8List pixels,
  int width,
  int height, {
  double tolerance = 32,
}) {
  final output = Uint8List.fromList(pixels);
  if (width < 2 || height < 2 || pixels.length != width * height * 4) {
    return output;
  }
  final border = <int>[];
  for (var x = 0; x < width; x++) {
    border.addAll([x, (height - 1) * width + x]);
  }
  for (var y = 1; y < height - 1; y++) {
    border.addAll([y * width, y * width + width - 1]);
  }
  if (border.where((i) => pixels[i * 4 + 3] < 32).length > border.length * .5) {
    return output;
  }
  final bins = <int, List<int>>{};
  for (final index in border) {
    final i = index * 4;
    if (pixels[i + 3] < 240) continue;
    final key =
        (pixels[i] >> 4) * 256 +
        (pixels[i + 1] >> 4) * 16 +
        (pixels[i + 2] >> 4);
    final bin = bins.putIfAbsent(key, () => [0, 0, 0, 0]);
    bin[0]++;
    bin[1] += pixels[i];
    bin[2] += pixels[i + 1];
    bin[3] += pixels[i + 2];
  }
  if (bins.isEmpty) return output;
  final dominant = bins.values.reduce((a, b) => a[0] >= b[0] ? a : b);
  if (dominant[0] < border.length * .25) return output;
  final background = [
    dominant[1] / dominant[0],
    dominant[2] / dominant[0],
    dominant[3] / dominant[0],
  ];
  final visited = Uint8List(width * height), queue = Int32List(width * height);
  var head = 0, tail = 0;
  void visit(int index) {
    if (visited[index] != 0) return;
    visited[index] = 1;
    final i = index * 4;
    final distance = math.sqrt(
      math.pow(pixels[i] - background[0], 2) +
          math.pow(pixels[i + 1] - background[1], 2) +
          math.pow(pixels[i + 2] - background[2], 2),
    );
    if (pixels[i + 3] < 16 || distance < tolerance + 12) {
      output[i + 3] = pixels[i + 3] < 16
          ? 0
          : (pixels[i + 3] * ((distance - tolerance) / 12).clamp(0, 1)).round();
      queue[tail++] = index;
    }
  }

  for (final index in border) {
    visit(index);
  }
  while (head < tail) {
    final index = queue[head++], x = index % width;
    if (x > 0) visit(index - 1);
    if (x < width - 1) visit(index + 1);
    if (index >= width) visit(index - width);
    if (index < width * (height - 1)) visit(index + width);
  }
  var visible = 0;
  for (var i = 3; i < output.length; i += 4) {
    if (output[i] > 30) visible++;
  }
  return visible < width * height * .015 ? Uint8List.fromList(pixels) : output;
}
