const fs = require("fs");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
const readmePath = path.join(rootDir, "README.md");
const backupPath = path.join(rootDir, "README.github.bak");

// Restore original GitHub README.md
if (fs.existsSync(backupPath)) {
  fs.copyFileSync(backupPath, readmePath);
  fs.unlinkSync(backupPath);
  console.log("\x1b[32m[NPM Restore]\x1b[0m Restored original GitHub README.md successfully.");
} else {
  // Fallback to git checkout
  try {
    const { execSync } = require("child_process");
    execSync("git checkout README.md", { stdio: "ignore" });
    console.log("\x1b[32m[NPM Restore]\x1b[0m Restored GitHub README.md via git.");
  } catch (_) {}
}
