const vscode = require("vscode");

function activate(context) {
  const showCliNotice = (feature) => {
    vscode.window.showWarningMessage(
      `Memingo: ${feature} necesita el CLI de Memingo. En vscode.dev están disponibles el resaltado de sintaxis, los iconos y los snippets; para ejecutar comandos usa VS Code de escritorio.`
    );
  };

  const commands = [
    ["memingo.run", "Ejecutar archivos"],
    ["memingo.init", "Inicializar proyectos"],
    ["memingo.repl", "Abrir el REPL"],
    ["memingo.serve", "Iniciar el servidor"],
    ["memingo.searchPackages", "Buscar paquetes"],
    ["memingo.installPackages", "Instalar paquetes"]
  ];

  for (const [id, label] of commands) {
    context.subscriptions.push(
      vscode.commands.registerCommand(id, () => showCliNotice(label))
    );
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
