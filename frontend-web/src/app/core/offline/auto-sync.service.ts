import { Injectable, inject, effect } from '@angular/core';
import { ConnectionService } from './connection.service';
import { SyncOfflineService } from './sync-offline.service';
import { ApiService } from '../../api.service';

@Injectable({
  providedIn: 'root'
})
export class AutoSyncService {
  private conn = inject(ConnectionService);
  private sync = inject(SyncOfflineService);
  private api = inject(ApiService);

  constructor() {
    this.api.currentUser.subscribe(user => {
      if (user?.empresa_id && this.conn.online()) this.sync.sincronizar().catch(() => {});
    });
    effect(() => {
      if (this.conn.online()) {
        this.sync.sincronizar().catch((err) => console.error('Auto-sync error', err));
      }
    });
  }
}
