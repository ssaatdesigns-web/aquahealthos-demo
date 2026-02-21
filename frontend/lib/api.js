export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `GET ${path} failed`);
  }
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `POST ${path} failed`);
  }
  return res.json();
}
