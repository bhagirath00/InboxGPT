#!/usr/bin/env node

/**
 * InboxGPT - npm executable launcher
 * Seamlessly routes command execution to the underlying Python TUI / CLI agent.
 */

const { spawn } = require("child_process");
const path = require("path");

function findPythonCommand() {
  const candidates = process.platform === "win32" 
    ? ["python", "py", "python3"] 
    : ["python3", "python"];
  return candidates[0];
}

function run() {
  const pythonCmd = findPythonCommand();
  const packageDir = path.resolve(__dirname, "..");
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
