import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ApiService, ChatConversation, ChatMessage } from './api.service';

@Component({
  selector: 'app-assistant',
  standalone: true,
  imports: [FormsModule, CommonModule],
  template: `
  <div class="chat-float" *ngIf="!open" (click)="openPanel()" title="Asistente virtual (CU23)">
    <span>💬</span>
    <span class="chat-badge" *ngIf="unread">●</span>
  </div>

  <div class="chat-panel" *ngIf="open">
    <header class="chat-head">
      <div>
        <strong>Asistente FashionStore</strong>
        <div class="chat-status">Respondo en línea · CU23</div>
      </div>
      <button class="modal-close" (click)="open = false">&times;</button>
    </header>

    <div class="chat-body" #scroll>
      <div *ngIf="!messages.length">
        <div class="chat-empty">
          <p>¡Hola! Soy el asistente de FashionStore. Pregúntame sobre pedidos, envíos, horarios, pagos o prendas.</p>
          <p class="chat-hint">Puedo seguir tus preguntas: por ejemplo, si hablamos de una prenda, pregúntame luego <em>“y en qué tallas hay”</em> o <em>“y cuánto cuesta”</em>.</p>
        </div>
      </div>

      <ng-container *ngFor="let m of messages">
        <div class="chat-msg" [class.assistant]="m.role === 'assistant'">
          {{ m.content }}
        </div>
        <div *ngIf="m.role === 'assistant' && m.suggestions?.length" class="chat-sug">
          <button *ngFor="let s of m.suggestions" class="btn btn-outline btn-sm"
            (click)="sendRaw(s)">{{ s }}</button>
        </div>
      </ng-container>

      <div *ngIf="busy" class="chat-msg assistant"><span class="typing">…</span></div>
    </div>

    <footer class="chat-foot">
      <input class="form-control" [(ngModel)]="draft" placeholder="Escribe tu consulta…"
        (keyup.enter)="send()" [disabled]="busy">
      <button class="btn btn-accent" (click)="send()" [disabled]="busy || !draft.trim()">Enviar</button>
    </footer>
  </div>
  `,
  styles: [`
    :host { position: fixed; right: 1.25rem; bottom: 1.25rem; z-index: 1200; }
    .chat-float {
      width: 3.5rem; height: 3.5rem; border-radius: 50%;
      background: linear-gradient(135deg, var(--accent, #e63946), var(--accent-dark, #b02a37));
      color: #fff; display: flex; align-items: center; justify-content: center;
      font-size: 1.4rem; cursor: pointer; box-shadow: 0 8px 24px rgba(0,0,0,.25);
    }
    .chat-badge { position: absolute; top: -.2rem; right: -.2rem; color: #ffd166; font-size: .9rem; }
    .chat-panel {
      width: 340px; max-width: calc(100vw - 1.5rem); height: 460px; max-height: 70vh;
      background: var(--surface, #fff); border: 1px solid var(--line, #e5e0d8);
      border-radius: 16px; display: flex; flex-direction: column; overflow: hidden;
      box-shadow: 0 18px 60px rgba(0,0,0,.28);
    }
    .chat-head { display:flex; justify-content:space-between; align-items:center; padding:.9rem 1rem; border-bottom:1px solid var(--line,#eee); background:#fbf7f1; }
    .chat-status { font-size:.75rem; color:var(--muted,#888); }
    .chat-body { flex:1; overflow-y:auto; padding:1rem; display:flex; flex-direction:column; gap:.6rem; }
    .chat-empty { color:var(--muted,#777); font-size:.9rem; }
    .chat-hint { font-size:.78rem; font-style:italic; margin-top:.4rem; }
    .chat-sug { display:flex; flex-wrap:wrap; gap:.4rem; }
    .chat-msg { max-width:85%; padding:.55rem .8rem; border-radius:12px; font-size:.88rem; white-space:pre-wrap; }
    .chat-msg:not(.assistant){ align-self:flex-end; background:#e63946; color:#fff; border-bottom-right-radius:4px; }
    .chat-msg.assistant { align-self:flex-start; background:#f3ede4; color:#2d2a26; border-bottom-left-radius:4px; }
    .chat-foot { display:flex; gap:.4rem; padding:.6rem; border-top:1px solid var(--line,#eee); }
    .typing { opacity:.5; }
  `],
})
export class AssistantComponent implements OnInit {
  @ViewChild('scroll') scrollEl?: ElementRef;

  open = false;
  messages: (ChatMessage & { suggestions?: string[] })[] = [];
  conversationId: number | null = null;
  draft = '';
  busy = false;
  unread = false;
  private triedLoad = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {}

  openPanel(): void {
    this.open = true;
    this.unread = false;
    if (!this.triedLoad && !this.messages.length) {
      this.triedLoad = true;
      this.api.getConversations().subscribe({
        next: (convs) => {
          if (convs.length) {
            const last = convs[0];
            this.conversationId = last.id;
            this.messages = (last.messages || []) as (ChatMessage & { suggestions?: string[] })[];
            this.scrollTop();
          }
        },
        error: () => {},
      });
    }
  }

  private scrollTop(): void {
    setTimeout(() => {
      const el = this.scrollEl?.nativeElement as HTMLElement | undefined;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }

  sendRaw(text: string): void {
    this.draft = text;
    this.send();
  }

  send(): void {
    const text = this.draft.trim();
    if (!text || this.busy) return;
    this.messages = [...this.messages, { role: 'user', content: text } as ChatMessage];
    this.draft = '';
    this.busy = true;
    this.scrollTop();
    this.api.sendChatMessage(text, this.conversationId).subscribe({
      next: (res) => {
        this.conversationId = res.conversation_id;
        this.messages = [...this.messages, {
          role: 'assistant',
          content: res.reply,
          suggestions: res.suggestions && res.suggestions.length ? res.suggestions : undefined,
        }];
        this.busy = false;
        this.scrollTop();
      },
      error: () => {
        this.messages = [...this.messages, {
          role: 'assistant',
          content: 'Lo siento, no pude conectarme con el asistente. Inténtalo de nuevo en un momento.',
        }];
        this.busy = false;
        this.scrollTop();
      },
    });
  }
}