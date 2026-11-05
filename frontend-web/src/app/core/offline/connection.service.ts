import { Injectable, signal } from '@angular/core';
import { fromEvent, merge, of } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ConnectionService {
  online = signal<boolean>(navigator.onLine);

  constructor() {
    const online$ = fromEvent(window, 'online').pipe(map(() => true));
    const offline$ = fromEvent(window, 'offline').pipe(map(() => false));
    merge(online$, offline$).subscribe((status) => this.online.set(status));
  }

  isOnline(): boolean {
    return this.online();
  }
}
