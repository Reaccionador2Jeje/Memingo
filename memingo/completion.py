MEMINGO_COMMANDS = (
    "repl doctor update-self init run eval check stats info deps clean dev build test serve",
    "add remove install update fmt completion",
)

MGOA_COMMANDS = (
    "search info list add install update remove publish completion",
)


def _flatten_commands(commands):
    return " ".join(commands).split()


def memingo_completion(shell):
    commands = _flatten_commands(MEMINGO_COMMANDS)
    return _completion_script("memingo", commands, shell)


def mgoa_completion(shell):
    commands = _flatten_commands(MGOA_COMMANDS)
    return _completion_script("mgoa", commands, shell)


def _completion_script(program, commands, shell):
    command_text = " ".join(commands)
    if shell == "bash":
        return (
            f"_{program}_completion() {{\n"
            "  local cur\n"
            "  cur=${COMP_WORDS[COMP_CWORD]}\n"
            "  COMPREPLY=( $(compgen -W '" + command_text + "' -- \"$cur\") )\n"
            "}\n"
            "complete -F " + f"_{program}_completion {program}\n"
        )
    if shell == "zsh":
        return (
            f"#compdef {program}\n"
            f"local -a commands\ncommands=({command_text.replace(' ', ' ')})\n"
            "_describe 'command' commands\n"
        )
    if shell == "fish":
        lines = [f"complete -c {program} -f"]
        for command in commands:
            lines.append(f"complete -c {program} -n '__fish_use_subcommand' -a '{command}'")
        return "\n".join(lines) + "\n"
    raise ValueError("Supported shells: bash, zsh, fish")
