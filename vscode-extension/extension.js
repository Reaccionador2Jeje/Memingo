const path = require("path");
const vscode = require("vscode");

function workspaceFolder(document) {
  if (document) {
    const folder = vscode.workspace.getWorkspaceFolder(document.uri);
    if (folder) return folder.uri.fsPath;
  }
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function terminal(command, name) {
  const existing = vscode.window.terminals.find((item) => item.name === name);
  const selected = existing || vscode.window.createTerminal(name);
  selected.show();
  selected.sendText(command, true);
}

function shellQuote(value) {
  const text = String(value);
  if (/^[A-Za-z0-9_.\-/\\:]+$/.test(text)) return text;
  return JSON.stringify(text);
}

function shellSeparator() {
  const shell = path.basename(vscode.env.shell || "").toLowerCase();
  return shell === "powershell.exe" || shell === "pwsh.exe" || shell === "pwsh" ? "; " : " && ";
}

function withWorkingDirectory(command, cwd) {
  return cwd ? `cd ${shellQuote(cwd)}${shellSeparator()}${command}` : command;
}

function sourceCommand(args, cwd) {
  const configuration = vscode.workspace.getConfiguration("memingo");
  const executable = configuration.get("executable", "memingo");
  const python = configuration.get("pythonExecutable", "python3");
  const command = executable === ""
    ? `${shellQuote(python)} -m memingo ${args.map(shellQuote).join(" ")}`
    : `${shellQuote(executable)} ${args.map(shellQuote).join(" ")}`;
  return withWorkingDirectory(command, cwd);
}

function packageCommand(args, cwd) {
  const configuration = vscode.workspace.getConfiguration("memingo");
  const executable = configuration.get("packageManagerExecutable", "mgoa");
  const python = configuration.get("pythonExecutable", "python3");
  const command = executable === ""
    ? `${shellQuote(python)} -m memingo.mgoa_cli ${args.map(shellQuote).join(" ")}`
    : `${shellQuote(executable)} ${args.map(shellQuote).join(" ")}`;
  return withWorkingDirectory(command, cwd);
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("memingo.run", async () => {
      const document = vscode.window.activeTextEditor?.document;
      if (!document) {
        vscode.window.showWarningMessage("Open a Memingo .mgo file first.");
        return;
      }
      if (document.isDirty) await document.save();
      const cwd = workspaceFolder(document);
      if (!cwd) {
        vscode.window.showErrorMessage("Open a Memingo workspace folder first.");
        return;
      }
      terminal(sourceCommand(["run", document.uri.fsPath], cwd), "Memingo Run");
    }),
    vscode.commands.registerCommand("memingo.init", async () => {
      const folder = await vscode.window.showOpenDialog({ canSelectFiles: false, canSelectFolders: true, canSelectMany: false, openLabel: "Initialize Here" });
      if (!folder?.length) return;
      const cwd = folder[0].fsPath;
      const name = await vscode.window.showInputBox({ prompt: "Memingo project name", value: "my-memingo-app" });
      terminal(sourceCommand(["init", cwd, "--name", name || "my-memingo-app"], cwd), "Memingo Init");
    }),
    vscode.commands.registerCommand("memingo.repl", () => {
      const cwd = workspaceFolder() || vscode.workspace.rootPath;
      if (!cwd) {
        vscode.window.showErrorMessage("Open a workspace folder first.");
        return;
      }
      terminal(sourceCommand(["repl"], cwd), "Memingo REPL");
    }),
    vscode.commands.registerCommand("memingo.searchPackages", () => {
      const cwd = workspaceFolder() || vscode.workspace.rootPath;
      terminal(packageCommand(["search"], cwd), "Memingo Packages");
    }),
    vscode.commands.registerCommand("memingo.installPackages", () => {
      const cwd = workspaceFolder() || vscode.workspace.rootPath;
      if (!cwd) {
        vscode.window.showErrorMessage("Open a workspace folder first.");
        return;
      }
      terminal(packageCommand(["install"], cwd), "Memingo Packages");
    }),
    vscode.commands.registerCommand("memingo.serve", () => {
      const cwd = workspaceFolder() || vscode.workspace.rootPath;
      if (!cwd) {
        vscode.window.showErrorMessage("Open a workspace folder first.");
        return;
      }
      terminal(sourceCommand(["serve", cwd], cwd), "Memingo Server");
    })
  );
}

function deactivate() {}
module.exports = { activate, deactivate };
