export interface UploadedManifest {
  categories: string[];
  scan_depth: 'quick' | 'standard' | 'deep';
}

const categories = ['prompt_injection', 'jailbreak', 'data_leak', 'harmful_output',
  'encoding_injection', 'malware_generation', 'toxicity'];

export function parseManifestInput(text: string): UploadedManifest {
  const value = JSON.parse(text);
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Manifest must contain a JSON object.');
  }
  const depth = value.scan_depth ?? 'standard';
  if (!['quick', 'standard', 'deep'].includes(depth)) throw new Error('Invalid manifest scan_depth.');
  const selected = value.categories ?? (depth === 'quick' ? categories.slice(0, 2) : categories);
  if (!Array.isArray(selected) || !selected.length || selected.some(c => !categories.includes(c))) {
    throw new Error('Manifest categories must be a nonempty array of supported category names.');
  }
  return { categories: [...new Set<string>(selected)], scan_depth: depth };
}
