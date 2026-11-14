"""Prototype normal-based reflection bands for otherwise unpatterned silver."""

GUIDE = r'''
function __silverGuide404(THREE, root) {
  root.updateMatrixWorld(true);
  const bounds = new THREE.Box3().setFromObject(root);
  const height = Math.max(1e-6, bounds.max.y - bounds.min.y);
  const white = new THREE.Color(1, 1, 1);
  const neutralMap = new WeakMap();
  function unpatterned(map) {
    if (!map) return true;
    if (neutralMap.has(map)) return neutralMap.get(map);
    const im = map.image, data = im && im.data;
    let ok = false;
    if (map.isDataTexture && data && data.BYTES_PER_ELEMENT === 1 && im.width > 0 && im.height > 0) {
      const channels = data.length / (im.width * im.height);
      if (channels === 3 || channels === 4) {
        const cols = new Array(32).fill(0), rows = new Array(16).fill(0);
        let mean = 0;
        for (let y = 0; y < 16; y++) for (let x = 0; x < 32; x++) {
          const px = Math.min(im.width - 1, Math.floor((x + 0.5) * im.width / 32));
          const py = Math.min(im.height - 1, Math.floor((y + 0.5) * im.height / 16));
          const i = (py * im.width + px) * channels;
          const value = (data[i] + data[i+1] + data[i+2]) / 765;
          mean += value / 512; cols[x] += value / 16; rows[y] += value / 32;
        }
        const std = a => Math.sqrt(a.reduce((s, v) => s + (v-mean)*(v-mean), 0) / a.length);
        ok = mean >= 0.70 && std(cols) <= 0.04 && std(rows) <= 0.04;
      }
    }
    neutralMap.set(map, ok);
    return ok;
  }
  root.traverse(node => {
    const m = node.material, g = node.geometry;
    if (!node.isMesh || node.isInstancedMesh || !g || !m || Array.isArray(m) || !m.isMeshStandardMaterial) return;
    if (m.vertexColors || g.getAttribute('color') || m.flatShading || m.envMap || m.opacity < 0.95 || (m.transmission || 0) > 0.05) return;
    const roughness = __silverRoughness404.has(m) ? __silverRoughness404.get(m) : m.roughness;
    if (m.metalness < 0.5 || roughness > 0.35 || !m.color || !unpatterned(m.map)) return;
    const rgb = [m.color.r, m.color.g, m.color.b];
    const high = Math.max(...rgb), low = Math.min(...rgb);
    if ((rgb[0]+rgb[1]+rgb[2])/3 < 0.25 || high-low > 0.22*high) return;
    const p = g.getAttribute('position'), n = g.getAttribute('normal');
    if (!p || !n || p.count !== n.count || !p.count) return;
    const colors = new Float32Array(p.count * 3);
    const normalMatrix = new THREE.Matrix3().getNormalMatrix(node.matrixWorld);
    const normal = new THREE.Vector3(), point = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) {
      normal.set(n.getX(i), n.getY(i), n.getZ(i)).applyMatrix3(normalMatrix).normalize();
      point.set(p.getX(i), p.getY(i), p.getZ(i)).applyMatrix4(node.matrixWorld);
      const v = (point.y - bounds.min.y) / height;
      const angle = Math.atan2(normal.x, normal.z);
      const drift = v*0.22 + Math.sin(v*9)*0.10;
      const bands = 0.79*Math.cos(angle*7+drift+1) + 0.15*Math.cos(angle*11-v*0.6+0.4) + 0.06*Math.sin(angle*3+v*0.5);
      const blend = Math.max(0, Math.min(1, (0.9-Math.abs(normal.y))/0.35));
      const value = (0.60+0.39*bands)*blend + (1-blend);
      colors[i*3] = value*0.97; colors[i*3+1] = value; colors[i*3+2] = value;
    }
    const geometry = g.clone();
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const material = m.clone();
    material.vertexColors = true;
    material.color.lerp(white, 0.5);
    material.needsUpdate = true;
    node.geometry = geometry; node.material = material;
  });
  return root;
}
'''


def silver_guide(source):
    needle = "export default function generate(THREE)"
    if source is None or source.count(needle) != 1 or "__silverGuide404" in source:
        return source
    # The winner's known metal pass overwrites authored roughness. Preserve it
    # only for eligibility; the original pass still executes unchanged.
    known = "m.metalness = 0.8; m.roughness = 0.2;"
    tagged = "__silverRoughness404.set(m, m.roughness); " + known
    source = source.replace(known, tagged, 1)
    source = source.replace(needle, "function __silverBase404(THREE)", 1)
    return "const __silverRoughness404 = new WeakMap();\n" + source + GUIDE + '''
export default function generate(THREE) {
  return __silverGuide404(THREE, __silverBase404(THREE));
}
'''
