export async function fetchStatus(): Promise<string> {
  try {
    const res = await fetch('http://localhost:8000/');
    if (!res.ok) {
      throw new Error('API error');
    }
    const data = await res.json();
    return `${data.message} (v${data.version})` || 'API reachable';
  } catch (err) {
    console.error('API Error:', err);
    return 'API unreachable';
  }
} 