import { writeFileSync } from 'fs';
import { join } from 'path';

const versionFilePath = join(process.cwd(), 'version.ts');

const options = { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit', 
    hour12: false, 
    timeZone: 'Asia/Chongqing'
};

const timestampParts = new Intl.DateTimeFormat('en-US', options).formatToParts(new Date());

const formattedTimestamp = `${timestampParts[4].value}-${timestampParts[0].value}-${timestampParts[2].value}_${timestampParts[6].value}.${timestampParts[8].value}.${timestampParts[10].value}`;

const content = `export const VERSION_TIMESTAMP = "v${formattedTimestamp}";\n`;

writeFileSync(versionFilePath, content);