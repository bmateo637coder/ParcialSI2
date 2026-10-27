import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

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

  generar() {
    this.cargando = true;
    this.error = '';
    this.resultado = null;
    this.http.post(`${environment.apiUrl}/reportes/ia`, { pregunta_natural: this.pregunta }).subscribe({
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
    this.http.post(`${environment.apiUrl}/reportes/ia/export`, { solicitud_id: this.resultado?.solicitud_id || 0, formato }).subscribe({
      next: (res: any) => {
        alert(res.mensaje + ' - ' + res.archivo_url);
      }
    });
  }
}
