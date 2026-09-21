import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';
import 'product_detail_screen.dart';

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  int _tab = 0;

  // Chat (CU23)
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  List<ChatMessage> _messages = [];
  List<String> _suggestions = [];
  int? _conversationId;
  bool _sending = false;

  // Recomendaciones (CU22)
  Recommendation? _recommendation;
  bool _recsLoading = true;
  String? _recsError;

  @override
  void initState() {
    super.initState();
    _loadRecommendations();
    _loadConversation();
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadRecommendations() async {
    setState(() {
      _recsLoading = true;
      _recsError = null;
    });
    try {
      final rec = await api.getRecommendations();
      if (!mounted) return;
      setState(() {
        _recommendation = rec;
        _recsLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _recsLoading = false;
        _recsError = e.toString();
      });
    }
  }

  Future<void> _loadConversation() async {
    try {
      final conversations = await api.getConversations();
      if (conversations.isEmpty) return;
      final conv = await api.getConversation(conversations.first.id);
      if (!mounted) return;
      setState(() {
        _conversationId = conv.id;
        _messages = conv.messages;
      });
      _scrollToBottom();
    } catch (_) {
      // Sin conversación previa; el chat arranca vacío.
    }
  }

  Future<void> _send() => _sendText(_messageController.text);

  Future<void> _sendText(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    setState(() {
      _messages = [
        ..._messages,
        ChatMessage(role: 'user', content: trimmed),
      ];
      _suggestions = [];
      _sending = true;
    });
    _scrollToBottom();
    _messageController.clear();
    try {
      final reply = await api.sendChat(trimmed, conversationId: _conversationId);
      if (!mounted) return;
      setState(() {
        _conversationId = reply.conversationId;
        _suggestions = reply.suggestions;
        _messages = [
          ..._messages,
          ChatMessage(role: 'assistant', content: reply.reply),
        ];
        _sending = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      showSnack(context, e.toString(), error: true);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Asistente IA'),
        bottom: TabBar(
          onTap: (i) => setState(() => _tab = i),
          tabs: const [
            Tab(text: 'Recomendaciones'),
            Tab(text: 'Chat'),
          ],
        ),
      ),
      body: _tab == 0 ? _buildRecommendations() : _buildChat(),
    );
  }

  Widget _buildRecommendations() {
    if (_recsLoading) return const LoadingView();
    if (_recsError != null) {
      return ErrorView(message: _recsError!, onRetry: _loadRecommendations);
    }
    final rec = _recommendation;
    if (rec == null || rec.items.isEmpty) {
      return const EmptyState(
          message: 'Compra antes para recibir recomendaciones (CU22).',
          icon: Icons.auto_awesome);
    }
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Icon(Icons.auto_awesome,
            size: 20, color: Theme.of(context).colorScheme.primary),
        const SizedBox(height: 4),
        Text(
          'Basado en: ${rec.source}',
          style: const TextStyle(fontSize: 12, color: Colors.grey),
        ),
        const SizedBox(height: 8),
        for (final item in rec.items)
          Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor:
                    Theme.of(context).colorScheme.primary.withValues(alpha: .12),
                child: Icon(Icons.checkroom,
                    color: Theme.of(context).colorScheme.primary),
              ),
              title: Text(item.name,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(
                  '${item.category} · ${money(item.basePrice)}\n${item.reason}'),
              isThreeLine: true,
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                    builder: (_) =>
                        ProductDetailScreen(productId: item.productId)),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildChat() {
    return Column(
      children: [
        Expanded(
          child: _messages.isEmpty
              ? const EmptyState(
                  message:
                      'Pregunta por prendas, disponibilidad o tu historial (CU23).\n\n'
                      'Ej: "¿Dónde hay camisas azules?" o "muéstrame mi última compra".',
                  icon: Icons.chat_outlined)
              : ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(12),
                  itemCount: _messages.length,
                  itemBuilder: (context, i) {
                    final m = _messages[i];
                    final mine = m.role == 'user';
                    return Align(
                      alignment:
                          mine ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.symmetric(vertical: 4),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.8),
                        decoration: BoxDecoration(
                          color: mine
                              ? const Color(0xFF5B2333)
                              : const Color(0xFFF1ECE6),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Text(
                          m.content,
                          style: TextStyle(
                              color: mine ? Colors.white : Colors.black87),
                        ),
                      ),
                    );
                  },
                ),
        ),
        if (_sending)
          const Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: EdgeInsets.only(left: 16, bottom: 4),
              child: Text('Escribiendo…',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
            ),
          ),
        if (!_sending && _suggestions.isNotEmpty)
          SizedBox(
            height: 96,
            child: SingleChildScrollView(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final s in _suggestions)
                    ActionChip(
                      avatar: const Icon(Icons.quickreply_outlined,
                          size: 16),
                      label: Text(s,
                          style: const TextStyle(fontSize: 12)),
                      backgroundColor: const Color(0xFFF7F1EA),
                      side: BorderSide(
                          color: Theme.of(context).colorScheme.primary
                              .withValues(alpha: .4)),
                      onPressed: () => _sendText(s),
                    ),
                ],
              ),
            ),
          ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                IconButton(
                  onPressed: () => setState(() {
                    _messages = [];
                    _suggestions = [];
                    _conversationId = null;
                  }),
                  icon: const Icon(Icons.add_comment_outlined),
                  tooltip: 'Nueva conversación',
                ),
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    onSubmitted: (_) => _send(),
                    decoration: const InputDecoration(
                      hintText: 'Escribe tu mensaje…',
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _sending ? null : _send,
                  child: const Icon(Icons.send),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}