// A successful Next build alone can leave raw Tailwind directives in the output.
// Fail CI on that regression: these directives are not understood by browsers.
const fs = require("node:fs");
const path = require("node:path");
const dir = path.join(process.cwd(), ".next", "static", "css");
const css = fs.readdirSync(dir).filter((name) => name.endsWith(".css"))
  .map((name) => fs.readFileSync(path.join(dir, name), "utf8")).join("\n");
if (!css || /@(?:tailwind|apply)\b/.test(css) || !/\.grid\s*\{/.test(css)) {
  throw new Error("Tailwind CSS was not compiled. Stop Next.js, move apps/web/.next aside, and rebuild.");
}
console.log("Production CSS verified: Tailwind directives compiled and layout utilities present.");
