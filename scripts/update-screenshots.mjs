import { readFile, writeFile, copyFile, mkdir } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const filenames = ['desktop.png', 'assembled.png', 'selected-part.png', 'mobile.png'];
// Require all real browser captures before writing files or inserting image links.
for (const name of filenames) {
  const data = await readFile(new URL(`web/artifacts/${name}`, root));
  if (!data.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) throw new Error(`Invalid screenshot PNG: ${name}`);
}
const readme = new URL('README.md', root);
const source = await readFile(readme, 'utf8');
const marker = /<!-- SCREENSHOTS:START -->[\s\S]*?<!-- SCREENSHOTS:END -->/;
if (!marker.test(source)) throw new Error('README screenshot markers are missing');
await mkdir(new URL('docs/screenshots/', root), { recursive: true });
for (const name of filenames) await copyFile(new URL(`web/artifacts/${name}`, root), new URL(`docs/screenshots/${name}`, root));
const content = `<!-- SCREENSHOTS:START -->
ภาพจาก Chrome ที่เปิด production build จริง สร้างโดย GitHub Actions หลัง browser acceptance tests ผ่าน

![Power Connex 3D Explorer บนเดสก์ท็อป](docs/screenshots/desktop.png)

![สถานะประกอบสมบูรณ์ 0%](docs/screenshots/assembled.png)

<details>
<summary>ดูภาพเมื่อเลือกชิ้นส่วนและหน้าจอมือถือ</summary>

![เลือกและโฟกัสชิ้นส่วนของรางไฟ](docs/screenshots/selected-part.png)

<img src="docs/screenshots/mobile.png" width="390" alt="Power Connex 3D Explorer บนมือถือ" />

</details>
<!-- SCREENSHOTS:END -->`;
await writeFile(readme, source.replace(marker, content));
console.log(`Updated README with ${filenames.length} real browser screenshots`);
