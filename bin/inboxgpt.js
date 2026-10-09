#!/usr/bin/env node

/**
 * InboxGPT - npm executable launcher
 * Seamlessly routes command execution to the underlying Python TUI / CLI agent.
 */

const { spawn, execSync } = require("child_process");
const path = require("path");

function findPythonCommand() {
  const candidates = process.platform === "win32" 
    ? ["python", "py", "python3"] 
    : ["python3", "python"];
  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: "ignore" });
      return cmd;
    } catch (_) {}
  }
  return candidates[0];
}

function ensureDependencies(pythonCmd, packageDir) {
  try {
    execSync(`${pythonCmd} -c "import textual, langgraph, google.auth"`, { stdio: "ignore" });
  } catch (_) {
    console.log("\x1b[36m[InboxGPT]\x1b[0m Installing required Python dependencies on first run...");
    try {
      execSync(`${pythonCmd} -m pip install -e "${packageDir}"`, { stdio: "inherit" });
      console.log("\x1b[32m[InboxGPT]\x1b[0m Setup complete!\n");
    } catch (err) {
      console.error("\x1b[31m[InboxGPT Error]\x1b[0m Failed to auto-install dependencies:", err.message);
      console.log("Please run manually: pip install -e .");
    }
  }
}

function run() {
  const pythonCmd = findPythonCommand();
  const packageDir = path.resolve(__dirname, "..");

  ensureDependencies(pythonCmd, packageDir);

  const env = { ...process.env };
  env.PYTHONPATH = env.PYTHONPATH 
    ? `${packageDir}${path.delimiter}${env.PYTHONPATH}`
    : packageDir;

  const args = ["-m", "inboxgpt.cli", ...process.argv.slice(2)];

  const child = spawn(pythonCmd, args, {
    stdio: "inherit",
    env: env,
  });

  child.on("error", (err) => {
    if (err.code === "ENOENT") {
      console.error("\x1b[31m[InboxGPT Error]\x1b[0m Python 3.10+ is required to run InboxGPT.");
      console.error("Please install Python from https://www.python.org/ or via your system package manager.");
    } else {
      console.error("\x1b[31m[InboxGPT Error]\x1b[0m Failed to spawn InboxGPT:", err.message);
    }
    process.exit(1);
  });

  child.on("exit", (code) => {
    process.exit(code || 0);
  });
}

run();
