import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

bootstrapApplication(App, appConfig)
  .then(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/ngsw-worker.js')
        .catch((err) => console.error('Service Worker registration failed:', err));
    }
  })
  .catch((err) => console.error(err));
