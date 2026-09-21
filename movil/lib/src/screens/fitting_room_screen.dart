import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:http/http.dart' as http;

class FittingRoomScreen extends StatefulWidget {
  final String productName;
  final String? initialColor;
  final String? imageUrl;

  const FittingRoomScreen({
    super.key,
    required this.productName,
    this.initialColor,
    this.imageUrl,
  });

  @override
  State<FittingRoomScreen> createState() => _FittingRoomScreenState();
}

class _FittingRoomScreenState extends State<FittingRoomScreen> {
  CameraController? _controller;
  PoseDetector? _detector;
  bool _cameraFailed = false;
  bool _processing = false;

  CameraDescription? _frontCam;
  CameraDescription? _backCam;
  CameraLensDirection _lens = CameraLensDirection.front;
  int _rotationDegrees = 90;

  // Pose del cuerpo (en coordenadas normalizadas 0..1 del frame ya rotado).
  bool _hasPose = false;
  double _centerFx = 0.5;
  double _centerFy = 0.48;
  double _widthFrac = 0.55;

  // Ajuste manual del usuario.
  double _scale = 1.0;
  double _opacity = 0.9;
  Offset _offset = Offset.zero;

  String _color = 'Rojo';
  ui.Image? _productImage;

  // Paleta para el overlay del vestidor (CU12).
  static const _palette = <String, Color>{
    'Rojo': Color(0xFFD32F2F),
    'Negro': Color(0xFF212121),
    'Blanco': Color(0xFFECEFF1),
    'Azul': Color(0xFF1976D2),
    'Verde': Color(0xFF388E3C),
    'Amarillo': Color(0xFFFBC02D),
    'Rosado': Color(0xFFEC407A),
    'Marrón': Color(0xFF795548),
    'Gris': Color(0xFF9E9E9E),
    'Naranja': Color(0xFFF57C00),
  };

  bool get _mirror => _lens == CameraLensDirection.front;

  @override
  void initState() {
    super.initState();
    _color = _palette.containsKey(widget.initialColor)
        ? widget.initialColor!
        : _palette.keys.first;
    _detector = PoseDetector(
      options: PoseDetectorOptions(mode: PoseDetectionMode.stream),
    );
    _initCamera();
    _loadProductImage();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() => _cameraFailed = true);
        return;
      }
      for (final c in cameras) {
        if (c.lensDirection == CameraLensDirection.front) {
          _frontCam ??= c;
        } else {
          _backCam ??= c;
        }
      }
      _frontCam ??= cameras.first;
      _backCam ??= cameras.first;
      await _openCamera(_frontCam!);
    } catch (_) {
      if (!mounted) return;
      setState(() => _cameraFailed = true);
    }
  }

  Future<void> _openCamera(CameraDescription camera) async {
    final rotation = camera.lensDirection == CameraLensDirection.front
        ? (360 - camera.sensorOrientation) % 360
        : camera.sensorOrientation;
    final controller = CameraController(
      camera,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    try {
      await controller.initialize();
      await controller.startImageStream(_processFrame);
      if (!mounted) {
        controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
        _lens = camera.lensDirection;
        _rotationDegrees = rotation;
        _cameraFailed = false;
        _hasPose = false;
        _centerFx = 0.5;
        _centerFy = 0.48;
        _widthFrac = 0.55;
        _scale = 1.0;
        _offset = Offset.zero;
      });
    } catch (_) {
      controller.dispose();
      if (!mounted) return;
      setState(() {
        _cameraFailed = true;
        _controller = null;
      });
    }
  }

  Future<void> _toggleCamera() async {
    if (_controller == null) return;
    final next = _lens == CameraLensDirection.front ? _backCam : _frontCam;
    if (next == null) return;
    final old = _controller;
    setState(() => _controller = null);
    old?.dispose();
    await _openCamera(next);
  }

  Future<void> _loadProductImage() async {
    final url = widget.imageUrl;
    if (url == null || url.trim().isEmpty) return;
    try {
      final resp = await http.get(Uri.parse(url));
      if (resp.statusCode != 200) return;
      final codec = await ui.instantiateImageCodec(resp.bodyBytes);
      final frame = await codec.getNextFrame();
      if (!mounted) return;
      setState(() => _productImage = frame.image);
    } catch (_) {}
  }

  Future<void> _processFrame(CameraImage frame) async {
    if (_processing || _detector == null) return;
    _processing = true;
    try {
      final nv21 = _yuv420ToNv21(frame);
      final input = InputImage.fromBytes(
        bytes: nv21,
        metadata: InputImageMetadata(
          size: ui.Size(frame.width.toDouble(), frame.height.toDouble()),
          rotation: _rotFromDegrees(_rotationDegrees),
          format: InputImageFormat.nv21,
          bytesPerRow: frame.width,
        ),
      );
      final poses = await _detector!.processImage(input);
      if (poses.isNotEmpty && mounted) {
        _updatePose(poses.first, frame);
      }
    } catch (_) {
      // Un frame sin detectar no debe romper el stream.
    } finally {
      _processing = false;
    }
  }

  void _updatePose(Pose pose, CameraImage frame) {
    final landmarks = pose.landmarks;
    final leftShoulder = landmarks[PoseLandmarkType.leftShoulder];
    final rightShoulder = landmarks[PoseLandmarkType.rightShoulder];
    if (leftShoulder == null || rightShoulder == null) return;

    // Con rotación 90° el frame se vuelve vertical: ancho = alto del sensor.
    final portraitW = frame.height.toDouble();
    final portraitH = frame.width.toDouble();

    final cx = (leftShoulder.x + rightShoulder.x) / 2 / portraitW;
    final cy = (leftShoulder.y + rightShoulder.y) / 2 / portraitH;
    final shoulderW = (rightShoulder.x - leftShoulder.x).abs() / portraitW;
    if (shoulderW <= 0 || shoulderW > 1.5) return;

    setState(() {
      _hasPose = true;
      _centerFx = cx.clamp(0.0, 1.0).toDouble();
      _centerFy = cy.clamp(0.0, 1.0).toDouble();
      _widthFrac = shoulderW.clamp(0.1, 1.2).toDouble();
    });
  }

  static InputImageRotation _rotFromDegrees(int degrees) {
    switch (degrees) {
      case 90:
        return InputImageRotation.rotation90deg;
      case 180:
        return InputImageRotation.rotation180deg;
      case 270:
        return InputImageRotation.rotation270deg;
      default:
        return InputImageRotation.rotation0deg;
    }
  }

  static Uint8List _yuv420ToNv21(CameraImage image) {
    final width = image.width;
    final height = image.height;
    final yPlane = image.planes.isEmpty ? null : image.planes[0];
    final nv21 = Uint8List(width * height + (width * height ~/ 2));
    if (yPlane == null) return nv21;

    // Plano Y (respetando el stride por fila).
    for (var row = 0; row < height; row++) {
      final srcStart = row * yPlane.bytesPerRow;
      final dstStart = row * width;
      for (var col = 0; col < width; col++) {
        nv21[dstStart + col] = yPlane.bytes[srcStart + col];
      }
    }

    // Croma: semi-planar (NV21 ya intercalado VU) o planar (3 planos).
    final chromaStart = width * height;
    final uvW = (width / 2).ceil();
    final uvH = (height / 2).ceil();

    if (image.planes.length >= 2) {
      final second = image.planes[1];
      final secondStride = second.bytesPerRow;
      final secondPixel = (second.bytesPerPixel ?? 0) > 0
          ? second.bytesPerPixel!
          : 2;
      final third = image.planes.length >= 3 ? image.planes[2] : null;
      final thirdStride = third?.bytesPerRow ?? secondStride;
      final thirdPixel = third == null
          ? secondPixel
          : ((third.bytesPerPixel ?? 0) > 0 ? third.bytesPerPixel! : 1);

      for (var row = 0; row < uvH; row++) {
        for (var col = 0; col < uvW; col++) {
          final dst = chromaStart + row * uvW * 2 + col * 2;
          if (third == null) {
            // Semi-planar: plane[1] trae pares V-U intercalados.
            final src = row * secondStride + col * secondPixel;
            nv21[dst] = second.bytes[src + 1];
            nv21[dst + 1] = second.bytes[src];
          } else {
            // Planar: plane[1] = V, plane[2] = U.
            final vSrc = row * secondStride + col * secondPixel;
            final uSrc = row * thirdStride + col * thirdPixel;
            nv21[dst] = second.bytes[vSrc];
            nv21[dst + 1] = third.bytes[uSrc];
          }
        }
      }
    }

    return nv21;
  }

  void _resetAdjust() {
    setState(() {
      _scale = 1.0;
      _opacity = 0.9;
      _offset = Offset.zero;
    });
  }

  @override
  void dispose() {
    _detector?.close();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = _palette[_color] ?? const Color(0xFFD32F2F);
    final cameraLive = _controller != null && _controller!.value.isInitialized;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vestidor virtual (CU12)'),
        actions: [
          if (cameraLive)
            IconButton(
              tooltip: 'Cambiar cámara',
              icon: const Icon(Icons.cameraswitch_outlined),
              onPressed: _toggleCamera,
            ),
          IconButton(
            tooltip: 'Restablecer ajustes',
            icon: const Icon(Icons.refresh),
            onPressed: _resetAdjust,
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: GestureDetector(
              onPanStart: (_) => _offset = _offset,
              onPanUpdate: (details) =>
                  setState(() => _offset += details.delta),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (cameraLive)
                    _mirror
                        ? Transform(
                            alignment: Alignment.center,
                            transform: Matrix4.diagonal3Values(-1, 1, 1),
                            child: CameraPreview(_controller!),
                          )
                        : CameraPreview(_controller!)
                  else if (_cameraFailed)
                    _DemoAvatar(color: color, image: _productImage)
                  else
                    const ColoredBox(color: Colors.black),
                  // Overlay de la prenda anclado al cuerpo detectado.
                  Positioned.fill(
                    child: CustomPaint(
                      painter: _GarmentPainter(
                        color: color,
                        image: _productImage,
                        hasPose: _hasPose,
                        centerFx: _centerFx,
                        centerFy: _centerFy,
                        widthFrac: _widthFrac,
                        mirror: _mirror,
                        scale: _scale,
                        opacity: _opacity,
                        offset: _offset,
                      ),
                      child: const SizedBox.expand(),
                    ),
                  ),
                  if (cameraLive)
                    Positioned(
                      top: 12,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.55),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            _hasPose
                                ? 'Cuerpo detectado · arrastra para ajustar'
                                : 'Mírate a la cámara para detectar el cuerpo',
                            style: const TextStyle(
                                color: Colors.white, fontSize: 12),
                          ),
                        ),
                      ),
                    ),
                  Positioned(
                    left: 12,
                    right: 12,
                    bottom: 12,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 10),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.6),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        widget.productName,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    alignment: WrapAlignment.center,
                    children: [
                      for (final entry in _palette.entries)
                        ChoiceChip(
                          label: Text(entry.key),
                          selected: _color == entry.key,
                          onSelected: (_) =>
                              setState(() => _color = entry.key),
                        ),
                    ],
                  ),
                  Row(
                    children: [
                      const Text('Tamaño', style: TextStyle(fontSize: 12)),
                      Expanded(
                        child: Slider(
                          value: _scale,
                          min: 0.6,
                          max: 2.2,
                          onChanged: (v) => setState(() => _scale = v),
                        ),
                      ),
                      const Text('Opacidad', style: TextStyle(fontSize: 12)),
                      SizedBox(
                        width: 120,
                        child: Slider(
                          value: _opacity,
                          min: 0.3,
                          max: 1.0,
                          onChanged: (v) => setState(() => _opacity = v),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GarmentPainter extends CustomPainter {
  final Color color;
  final ui.Image? image;
  final bool hasPose;
  final double centerFx;
  final double centerFy;
  final double widthFrac;
  final bool mirror;
  final double scale;
  final double opacity;
  final Offset offset;

  _GarmentPainter({
    required this.color,
    this.image,
    this.hasPose = false,
    this.centerFx = 0.5,
    this.centerFy = 0.48,
    this.widthFrac = 0.55,
    this.mirror = true,
    this.scale = 1.0,
    this.opacity = 0.9,
    this.offset = Offset.zero,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    final cx = (mirror ? 1 - centerFx : centerFx) * w + offset.dx;
    final cy = centerFy * h + offset.dy;
    final shoulderW = widthFrac * w * scale;

    if (image != null && hasPose) {
      // Dibujar la foto real del producto anclada a los hombros.
      final dstW = shoulderW * 1.7;
      final dstH = dstW * (image!.height / image!.width);
      final top = cy - dstH * 0.2;
      final dst = Rect.fromLTWH(cx - dstW / 2, top, dstW, dstH);

      canvas.saveLayer(
        dst,
        Paint()..color = Colors.white.withValues(alpha: opacity),
      );
      canvas.drawImageRect(
        image!,
        Rect.fromLTWH(
            0, 0, image!.width.toDouble(), image!.height.toDouble()),
        dst,
        Paint(),
      );
      canvas.restore();

      // Marcadores de hombros para feedback de detección.
      final dot = Paint()..color = Colors.amber;
      canvas.drawCircle(Offset(cx - shoulderW / 2, cy), 4, dot);
      canvas.drawCircle(Offset(cx + shoulderW / 2, cy), 4, dot);
      return;
    }

    // Silueta genérica como respaldo (sin pose o sin imagen).
    final rectW = shoulderW * (hasPose ? 1.25 : 1.0);
    final rectH = widthFrac * w * 1.15;
    final rect = Rect.fromCenter(
      center: Offset(cx, cy + rectH * 0.12),
      width: rectW,
      height: rectH,
    );
    final paint = Paint()..color = color.withValues(alpha: opacity);

    final path = Path()
      ..moveTo(rect.left, rect.top + rect.height * 0.1)
      ..quadraticBezierTo(
          rect.center.dx - 10, rect.top, rect.center.dx, rect.top)
      ..quadraticBezierTo(
          rect.center.dx + 10, rect.top, rect.right, rect.top + rect.height * 0.1)
      ..lineTo(rect.right, rect.bottom)
      ..quadraticBezierTo(rect.center.dx, rect.bottom + rect.height * 0.08,
          rect.left, rect.bottom)
      ..close();

    canvas.drawPath(path, paint);
    canvas.drawPath(
      path,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..color = Colors.white.withValues(alpha: 0.9),
    );
  }

  @override
  bool shouldRepaint(covariant _GarmentPainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.image != image ||
      oldDelegate.hasPose != hasPose ||
      oldDelegate.centerFx != centerFx ||
      oldDelegate.centerFy != centerFy ||
      oldDelegate.widthFrac != widthFrac ||
      oldDelegate.mirror != mirror ||
      oldDelegate.scale != scale ||
      oldDelegate.opacity != opacity ||
      oldDelegate.offset != offset;
}

class _DemoAvatar extends StatelessWidget {
  final Color color;
  final ui.Image? image;

  const _DemoAvatar({required this.color, this.image});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFEDE7F6),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.face, size: 96, color: Color(0xFF9E9390)),
            const SizedBox(height: 4),
            if (image != null)
              RawImage(
                image: image,
                height: 150,
                width: 120,
                fit: BoxFit.contain,
              )
            else
              Container(
                width: 140,
                height: 150,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.8),
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(30),
                    topRight: Radius.circular(30),
                  ),
                ),
                child:
                    const Icon(Icons.checkroom, size: 60, color: Colors.white),
              ),
            const SizedBox(height: 14),
            const Text('Modo demostración: sin cámara disponible.',
                style: TextStyle(fontWeight: FontWeight.w600)),
            const Text('Prueba el overlay de la prenda con distintos colores.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
      ),
    );
  }
}