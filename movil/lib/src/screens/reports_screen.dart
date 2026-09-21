import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../theme.dart';
import '../widgets.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  int _tab = 0;

  // Dashboard (CU25)
  DashboardReport? _report;
  bool _loading = true;
  String? _error;

  // Voz (CU24)
  final _voiceController = TextEditingController();
  VoiceReport? _voice;
  bool _voiceLoading = false;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  @override
  void dispose() {
    _voiceController.dispose();
    super.dispose();
  }

  Future<void> _loadDashboard() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final now = DateTime.now();
      final from =
          DateTime(now.year, now.month - 1, now.day); // último mes
      final report = await api.getDashboard(
        desde: '${from.year.toString().padLeft(4, '0')}-${from.month.toString().padLeft(2, '0')}-${from.day.toString().padLeft(2, '0')}',
        hasta: '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}',
      );
      if (!mounted) return;
      setState(() {
        _report = report;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _runVoice(String? preset) async {
    final command = preset ?? _voiceController.text.trim();
    if (command.isEmpty) {
      showSnack(context, 'Escribe o selecciona un comando (CU24).', error: true);
      return;
    }
    setState(() {
      _voiceLoading = true;
      _voice = null;
    });
    try {
      final result = await api.voiceReport(command);
      if (!mounted) return;
      setState(() {
        _voice = result;
        _voiceLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _voiceLoading = false);
      showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reportes'),
        bottom: TabBar(
          onTap: (i) => setState(() => _tab = i),
          tabs: const [
            Tab(text: 'Dashboard'),
            Tab(text: 'Comando de voz'),
          ],
        ),
      ),
      body: _tab == 0 ? _buildDashboard() : _buildVoice(),
    );
  }

  Widget _buildDashboard() {
    if (_loading) return const LoadingView();
    if (_error != null) {
      return ErrorView(message: _error!, onRetry: _loadDashboard);
    }
    final r = _report;
    if (r == null) return const EmptyState(message: 'Sin datos.');
    return RefreshIndicator(
      onRefresh: _loadDashboard,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (r.narrative != null)
            Card(
              color: const Color(0xFF5B2333).withValues(alpha: 0.07),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.auto_awesome, color: Color(0xFF5B2333)),
                    const SizedBox(width: 10),
                    Expanded(
                        child: Text(r.narrative!,
                            style: const TextStyle(fontWeight: FontWeight.w500))),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 8),
          _KpiGrid(kpis: r.kpis),
          const SizedBox(height: 16),
          Text('Ventas por día',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: _SalesBars(points: r.salesSeries),
            ),
          ),
          const SizedBox(height: 16),
          Text('Por categoría',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          for (final c in r.byCategory)
            Card(
              child: ListTile(
                leading: const Icon(Icons.category_outlined),
                title: Text(c.categoryName),
                trailing: Text('${money(c.sales)} · ${c.units} u'),
              ),
            ),
          const SizedBox(height: 12),
          Text('Top productos',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          for (final t in r.topProducts)
            Card(
              child: ListTile(
                leading: const Icon(Icons.star_outline, color: Color(0xFFC9A227)),
                title: Text(t.name),
                trailing: Text('${t.units} u · ${money(t.revenue)}'),
              ),
            ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildVoice() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _voiceController,
          decoration: const InputDecoration(
            labelText: 'Comando (CU24)',
            hintText: '"reporte de ventas de la última semana"',
            prefixIcon: Icon(Icons.mic),
          ),
          onSubmitted: (_) => _runVoice(null),
        ),
        const SizedBox(height: 10),
        AppPrimaryButton(
          label: 'Ejecutar comando',
          icon: Icons.play_arrow,
          loading: _voiceLoading,
          onPressed: () => _runVoice(null),
        ),
        const SizedBox(height: 16),
        Text('Ejemplos', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final p in [
              'Reporte de ventas de la última semana',
              'Top 5 productos del mes',
              'Ventas por categoría',
            ])
              ActionChip(
                label: Text(p, style: const TextStyle(fontSize: 12)),
                onPressed: () {
                  _voiceController.text = p;
                  _runVoice(p);
                },
              ),
          ],
        ),
        const SizedBox(height: 20),
        if (_voiceLoading)
          const Center(child: CircularProgressIndicator())
        else if (_voice != null)
          _VoiceResult(result: _voice!),
      ],
    );
  }
}

class _KpiGrid extends StatelessWidget {
  final ReportKpis kpis;

  const _KpiGrid({required this.kpis});

  @override
  Widget build(BuildContext context) {
    final items = <(String, String, IconData)>[
      ('Ventas', money(kpis.totalSales), Icons.attach_money),
      ('Pedidos', '${kpis.totalOrders}', Icons.receipt_long),
      ('Ticket medio', money(kpis.avgOrder), Icons.show_chart),
      ('Reservas', '${kpis.reservations}', Icons.event_seat),
      ('Unidades disp.', '${kpis.totalUnitsAvailable}', Icons.inventory_2),
      ('Stock bajo', '${kpis.lowStockVariants}', Icons.warning_amber),
      ('Promos', '${kpis.activePromotions}', Icons.percent),
      ('Dsctos. aplic.', money(kpis.discountAmount), Icons.sell),
    ];
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 2.4,
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      children: [
        for (final (label, value, icon) in items)
          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                children: [
                  Icon(icon, color: const Color(0xFF5B2333)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(value,
                            style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                fontSize: 16)),
                        Text(label,
                            style: const TextStyle(
                                fontSize: 11, color: Colors.grey)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _SalesBars extends StatelessWidget {
  final List<SalesPoint> points;

  const _SalesBars({required this.points});

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return const Text('Sin ventas en el período.',
          style: TextStyle(color: Colors.grey));
    }
    final maxV = points.map((p) => p.amount).reduce((a, b) => a > b ? a : b);
    return SizedBox(
      height: 140,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final p in points)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text('${p.amount.round()}',
                        style: const TextStyle(fontSize: 9, color: Colors.grey)),
                    const SizedBox(height: 2),
                    Container(
                      height: maxV == 0 ? 2 : (p.amount / maxV) * 100,
                      decoration: const BoxDecoration(
                        color: Color(0xFF5B2333),
                        borderRadius:
                            BorderRadius.vertical(top: Radius.circular(4)),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      p.date.length >= 5 ? p.date.substring(5) : p.date,
                      style: const TextStyle(fontSize: 8, color: Colors.grey),
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

class _VoiceResult extends StatelessWidget {
  final VoiceReport result;

  const _VoiceResult({required this.result});

  @override
  Widget build(BuildContext context) {
    if (!result.recognized) {
      return Card(
        color: const Color(0xFFFFECB3),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Text(result.message,
              style: const TextStyle(fontWeight: FontWeight.w600)),
        ),
      );
    }
    final data = result.data;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.check_circle, color: Color(0xFF2E7D32)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Reconocido como: ${result.intent.reportType ?? '-'}'
                    ' · ${result.message}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (data != null) ...[
              Text('Ventas en el período: ${money(data.kpis.totalSales)} '
                  '(${data.kpis.totalOrders} pedidos)',
                  style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 8),
              Text('Incluye:',
                  style: Theme.of(context).textTheme.titleSmall),
              for (final t in data.topProducts)
                Text('• ${t.name}: ${t.units} u (${money(t.revenue)})'),
              for (final c in data.byCategory)
                Text('• ${c.categoryName}: ${money(c.sales)}'),
            ],
          ],
        ),
      ),
    );
  }
}