import { writeFileSync } from 'fs';
import { join } from 'path';

const versionFilePath = join(process.cwd(), 'version.ts');
const timestamp = new Date().toISOString();

const content = `export const VERSION_TIMESTAMP = "v${timestamp}";\n`;

writeFileSync(versionFilePath, content);