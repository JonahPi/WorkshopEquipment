import PocketBase from 'pocketbase';

let _pb: PocketBase | null = null;

/** Initialise (or re-initialise) the PocketBase singleton with runtime credentials. */
export function initPb(url: string, token: string): PocketBase {
  _pb = new PocketBase(url);
  // authStore.save sets the Authorization header on every request
  _pb.authStore.save(token, null);
  return _pb;
}

/** Return the current PocketBase instance. Throws if not yet initialised. */
export function getPb(): PocketBase {
  if (!_pb) throw new Error('PocketBase not initialised — call initPb() first');
  return _pb;
}

export function resetPb(): void {
  _pb = null;
}
