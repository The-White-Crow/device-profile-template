const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
let passed = 0;
for (const vendor of fs.readdirSync(path.join(root, "vendors"))) {
  const dir = path.join(root, "vendors", vendor, "codecs");
  if (!fs.existsSync(dir)) continue;
  for (const file of fs.readdirSync(dir)) {
    const match = /^test_(decode|encode)_(.+)\.json$/.exec(file);
    if (!match) continue;
    const method = match[1] === "decode" ? "decodeUplink" : "encodeDownlink";
    const source = fs.readFileSync(path.join(dir, match[2] + ".js"), "utf8");
    const tests = JSON.parse(fs.readFileSync(path.join(dir, file), "utf8"));
    assert.ok(tests.length > 0, file + " must have test cases");
    for (const test of tests) {
      const sandbox = { input: test.input };
      vm.createContext(sandbox);
      vm.runInContext(source, sandbox, { timeout: 1000 });
      const actual = vm.runInContext(method + "(input)", sandbox, { timeout: 1000 });
      assert.deepStrictEqual(JSON.parse(JSON.stringify(actual)), test.expected,
        vendor + "/" + file + ": " + test.name);
      passed++;
      console.log("PASS " + vendor + ": " + test.name);
    }
  }
}
assert.ok(passed > 0, "No codec tests found");
console.log(passed + " codec tests passed");

