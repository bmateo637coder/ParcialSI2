const runtime = globalThis as typeof globalThis & { __FASHIONSTORE_CONFIG__?: { apiUrl?: string } };

export const environment = {
  production: true,
  apiUrl: runtime.__FASHIONSTORE_CONFIG__?.apiUrl || '/api',
};
