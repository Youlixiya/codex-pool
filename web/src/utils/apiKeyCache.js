const STORAGE_KEY = "codex-pool-api-key-secrets";

function readMap() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function cacheApiKey(id, key) {
  if (!id || !key) return;
  const map = readMap();
  map[String(id)] = key;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

export function getCachedApiKey(id) {
  return readMap()[String(id)] || "";
}

export function removeCachedApiKey(id) {
  const map = readMap();
  delete map[String(id)];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}
