import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:fashionstore_movil/src/garment_image.dart';

void main() {
  test('Quita fondo exterior y preserva detalles blancos interiores', () {
    const w = 30, h = 30;
    final pixels = Uint8List(w * h * 4)..fillRange(0, w * h * 4, 255);
    for (var y = 5; y < 25; y++) {
      for (var x = 5; x < 25; x++) {
        final i = (y * w + x) * 4;
        pixels[i] = 30;
        pixels[i + 1] = 70;
        pixels[i + 2] = 140;
      }
    }
    final center = (15 * w + 15) * 4;
    pixels[center] = 255;
    pixels[center + 1] = 255;
    pixels[center + 2] = 255;
    final output = removeGarmentBackground(pixels, w, h);
    expect(output[3], 0);
    expect(output[center + 3], 255);
    expect(output[(6 * w + 6) * 4 + 3], 255);
    expect(pixels[3], 255);
    expect(garmentAlphaBounds(output, w, h), (
      left: 2,
      top: 2,
      width: 26,
      height: 26,
    ));
  });
  test('Conserva PNG transparente sin volver a recortar la prenda', () {
    final pixels = Uint8List(10 * 10 * 4);
    pixels[44] = 255;
    pixels[47] = 255;
    expect(removeGarmentBackground(pixels, 10, 10), pixels);
  });
}
