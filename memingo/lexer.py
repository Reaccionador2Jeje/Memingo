from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    line: int
    column: int


KEYWORDS = {
    "vibe", "ritual", "drop", "when", "nah", "grind", "spill", "borrow",
    "based", "cringe", "ghost",
}


class LexerError(Exception):
    pass


class Lexer:
    two_character = ("==", "!=", "<=", ">=", "&&", "||")

    def __init__(self, source: str):
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1

    def tokenize(self):
        tokens = []
        while self.index < len(self.source):
            char = self.source[self.index]

            if char in " \t\r":
                self._advance()
            elif char == "\n":
                tokens.append(Token("NEWLINE", "\n", self.line, self.column))
                self._advance()
            elif char == "#":
                while self.index < len(self.source) and self.source[self.index] != "\n":
                    self._advance()
            elif char == '"':
                tokens.append(self._string())
            elif char.isdigit():
                tokens.append(self._number())
            elif char.isalpha() or char == "_":
                tokens.append(self._identifier())
            else:
                pair = self.source[self.index:self.index + 2]
                if pair in self.two_character:
                    tokens.append(Token("OP", pair, self.line, self.column))
                    self._advance()
                    self._advance()
                elif char in "=+-*/%<>!(){}[],;:.?":
                    kind = {
                        "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH",
                        "%": "PERCENT", "=": "EQUAL", "<": "OP", ">": "OP",
                        "!": "OP", "(": "LPAREN", ")": "RPAREN", "{": "LBRACE",
                        "}": "RBRACE", "[": "LBRACKET", "]": "RBRACKET",
                        ",": "COMMA", ";": "SEMICOLON", ":": "COLON", ".": "DOT",
                    }[char]
                    value = char if kind == "OP" else char
                    tokens.append(Token(kind, value, self.line, self.column))
                    self._advance()
                else:
                    raise LexerError(f"Unexpected character {char!r} at line {self.line}, column {self.column}")

        tokens.append(Token("EOF", None, self.line, self.column))
        return tokens

    def _advance(self):
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _string(self):
        line, column = self.line, self.column
        self._advance()
        result = []
        escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
        while self.index < len(self.source) and self.source[self.index] != '"':
            char = self._advance()
            if char == "\\":
                if self.index >= len(self.source):
                    raise LexerError(f"Unfinished escape sequence at line {line}, column {column}")
                escaped = self._advance()
                if escaped not in escapes:
                    raise LexerError(f"Unknown escape \\{escaped} at line {line}, column {column}")
                result.append(escapes[escaped])
            elif char == "\n":
                raise LexerError(f"Unterminated string at line {line}, column {column}")
            else:
                result.append(char)
        if self.index >= len(self.source):
            raise LexerError(f"Unterminated string at line {line}, column {column}")
        self._advance()
        return Token("STRING", "".join(result), line, column)

    def _number(self):
        line, column = self.line, self.column
        start = self.index
        dots = 0
        while self.index < len(self.source):
            char = self.source[self.index]
            if char.isdigit():
                self._advance()
            elif char == "." and dots == 0:
                dots += 1
                self._advance()
            else:
                break
        text = self.source[start:self.index]
        value = float(text) if dots else int(text)
        return Token("NUMBER", value, line, column)

    def _identifier(self):
        line, column = self.line, self.column
        start = self.index
        while self.index < len(self.source):
            char = self.source[self.index]
            if char.isalnum() or char == "_":
                self._advance()
            else:
                break
        text = self.source[start:self.index]
        kind = text.upper() if text in KEYWORDS else "IDENTIFIER"
        return Token(kind, text, line, column)
