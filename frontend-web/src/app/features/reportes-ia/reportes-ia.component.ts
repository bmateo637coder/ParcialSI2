import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-reportes-ia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reportes-ia.component.html'
})
export class ReportesIaComponent {
  private http = inject(HttpClient);
  pregunta = '';
  resultado: any = null;
  cargando = false;
  error = '';
  desde = '';
  hasta = '';
  escuchando = false;

  escuchar() {
    const Speech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Speech) { this.error = 'Este navegador no admite dictado. Puedes escribir la solicitud.'; return; }
    const recognition = new Speech();
    recognition.lang = 'es-BO';
    recognition.onresult = (event: any) => { this.pregunta = event.results[0][0].transcript; };
    recognition.onend = () => { this.escuchando = false; };
    recognition.onerror = () => { this.error = 'No se pudo escuchar. Comprueba el permiso del micrófono.'; this.escuchando = false; };
    this.escuchando = true;
    recognition.start();
  }

  porcentaje(value: number): number {
    const max = Math.max(...(this.resultado?.grafico?.datos || [1]).map((n:number)=>Math.abs(n)), 1);
    return Math.abs(value) / max * 100;
  }

  generar() {
    this.cargando = true;
    this.error = '';
    this.resultado = null;
    const filtros = { ...(this.desde ? { fecha_desde: this.desde } : {}), ...(this.hasta ? { fecha_hasta: this.hasta } : {}) };
    this.http.post(`${environment.apiUrl}/reportes/ia`, { pregunta_natural: this.pregunta, filtros }).subscribe({
      next: (res) => {
        this.resultado = res;
        this.cargando = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Error al generar reporte';
        this.cargando = false;
      }
    });
  }

  exportar(formato: 'pdf' | 'excel') {
    this.http.get(`${environment.apiUrl}/reportes/ia/${this.resultado.solicitud_id}/archivo?formato=${formato}`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url; link.download = `reporte-${this.resultado.solicitud_id}.${formato === 'excel' ? 'xlsx' : 'pdf'}`;
        link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      },
      error: () => { this.error = 'No se pudo descargar el reporte.'; }
    });
  }
}
