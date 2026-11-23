import { cp, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import process from "node:process";

const outDir = process.env.MAKEFUN_OUTPUT_DIR || "/output";
const source = join(process.cwd(), "VIDEO.json");
const target = join(outDir, "VIDEO.json");

await mkdir(dirname(target), { recursive: true });
await cp(source, target);
console.log(`copied ${source} to ${target}`);
