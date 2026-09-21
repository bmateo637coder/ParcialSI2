import 'package:flutter/material.dart';

import 'models.dart';

void showSnack(BuildContext context, String message,
    {bool error = false}) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
    content: Text(message),
    backgroundColor: error ? AppColorsError.danger : const Color(0xFF2E7D32),
    behavior: SnackBarBehavior.floating,
  ));
}

// Local alias to keep the widget file from importing the theme drawer twice.
class AppColorsError {
  static const danger = Color(0xFFC62828);
}

class LoadingView extends StatelessWidget {
  final String message;

  const LoadingView({super.key, this.message = 'Cargando…'});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(message, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;

  const ErrorView({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off, size: 56, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Reintentar'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String message;
  final IconData icon;

  const EmptyState({super.key, required this.message, this.icon = Icons.inbox});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 56, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class ProductImage extends StatelessWidget {
  final String? url;
  final double size;

  const ProductImage({super.key, this.url, this.size = 72});

  @override
  Widget build(BuildContext context) {
    final hasUrl = url != null && url!.trim().isNotEmpty;
    Widget fallback = Container(
      width: size,
      height: size,
      color: const Color(0xFFF0E7DE),
      child: const Icon(Icons.checkroom, color: AppColorsError.danger, size: 30),
    );
    if (!hasUrl) return fallback;
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: Image.network(
        url!,
        width: size,
        height: size,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => fallback,
        loadingBuilder: (context, child, progress) {
          if (progress == null) return child;
          return fallback;
        },
      ),
    );
  }
}

class PriceText extends StatelessWidget {
  final double value;
  final bool showStrikethrough;

  const PriceText(this.value, {super.key, this.showStrikethrough = false});

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.titleMedium?.copyWith(
          color: AppColorsError.danger,
          fontWeight: FontWeight.w700,
          decoration:
              showStrikethrough ? TextDecoration.lineThrough : null,
        );
    return Text(money(value), style: style);
  }
}

class StatusBadge extends StatelessWidget {
  final String status;

  const StatusBadge(this.status, {super.key});

  Color get _color {
    final s = status.toUpperCase();
    if (s.contains('PEND') || s == 'FALLIDO') return const Color(0xFFB26A00);
    if (s.contains('CANC')) return const Color(0xFFBDBDBD);
    if (s.contains('RECHA')) return const Color(0xFFC62828);
    if (s.contains('ATEND') ||
        s.contains('PAGAD') ||
        s.contains('ENTREG') ||
        s.contains('APROB') ||
        s.contains('COMPLET')) return const Color(0xFF2E7D32);
    return const Color(0xFF5B2333);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        status,
        style: TextStyle(
          color: _color,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    );
  }
}

class SectionHeader extends StatelessWidget {
  final String title;
  final Widget? trailing;

  const SectionHeader(this.title, {super.key, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Row(
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const Spacer(),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

class AppHeader extends StatelessWidget {
  final String title;

  const AppHeader(this.title, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.storefront, color: AppColorsError.danger),
              const SizedBox(width: 8),
              Text(
                'FashionStore',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: AppColorsError.danger,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(title, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}