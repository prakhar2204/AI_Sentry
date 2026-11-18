import { describe, expect, it } from 'vitest';
import { parseManifestInput } from '../services/manifestInput';

describe('uploaded manifests', () => {
  it('reads selected categories and depth instead of silently running defaults', () => {
    expect(parseManifestInput('{"categories":["toxicity"],"scan_depth":"deep"}')).toEqual({categories:['toxicity'],scan_depth:'deep'});
  });
  it.each(['broken', 'null', '[]', '{"categories":[]}', '{"categories":["unknown"]}', '{"scan_depth":"extreme"}'])(
    'rejects invalid manifest %s', text => expect(() => parseManifestInput(text)).toThrow(),
  );
});
