// Este ficheiro é o ponto de entrada (main) da sua extensão.
// Ele é carregado quando a extensão é ativada.

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {

    // A extensão stagerun-syntax foi ativada.
    // Se esta mensagem aparecer no log "Extension Host (Remote)",
    // significa que a extensão está a ser executada no servidor.
    console.log('"stagerun-syntax" activated!');

    // Nota: Para este caso, a principal contribuição (sintaxe)
    // é feita via 'contributes' no package.json, e é tratada pela parte 'ui'.
    // Esta função 'activate' é principalmente para futuras funcionalidades
    // de 'workspace' (IntelliSense, Comandos, etc.).
}

// Este método é chamado quando a sua extensão é desativada
function deactivate() {}

module.exports = {
    activate,
    deactivate
}