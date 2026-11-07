from dataclasses import dataclass
from .lexer import Lexer, LexerError, Token


@dataclass
class Program:
    statements: list


@dataclass
class Borrow:
    package: object


@dataclass
class Let:
    name: str
    value: object


@dataclass
class Assign:
    name: str
    value: object


@dataclass
class Say:
    value: object


@dataclass
class Return:
    value: object


@dataclass
class If:
    condition: object
    then_branch: list
    else_branch: list


@dataclass
class While:
    condition: object
    body: list


@dataclass
class Function:
    name: str
    params: list
    body: list


@dataclass
class Literal:
    value: object


@dataclass
class Variable:
    name: str


@dataclass
class ListExpression:
    items: list


@dataclass
class MapExpression:
    entries: list


@dataclass
class Get:
    target: object
    key: object


@dataclass
class Binary:
    operator: str
    left: object
    right: object


@dataclass
class Unary:
    operator: str
    operand: object


@dataclass
class Call:
    callee: object
    arguments: list


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    def parse(self):
        statements = []
        self._skip_separators()
        while not self._check("EOF"):
            statements.append(self._statement())
            self._skip_separators()
        return Program(statements)

    def _statement(self):
        if self._match("VIBE"):
            return self._let_statement()
        if self._match("RITUAL"):
            return self._function_statement()
        if self._match("WHEN"):
            return self._if_statement()
        if self._match("GRIND"):
            return self._while_statement()
        if self._match("DROP"):
            return Return(self._expression())
        if self._match("SPILL"):
            return Say(self._expression())
        if self._match("BORROW"):
            return Borrow(self._expression())
        if self._check("IDENTIFIER"):
            name = self._advance().value
            if self._match("EQUAL"):
                return Assign(name, self._expression())
            self.index -= 1
        expr = self._expression()
        return expr

    def _let_statement(self):
        name = self._consume("IDENTIFIER", "Expected variable name after 'vibe'").value
        self._consume("EQUAL", "Expected '=' after variable name")
        return Let(name, self._expression())

    def _function_statement(self):
        name = self._consume("IDENTIFIER", "Expected function name").value
        self._consume("LPAREN", "Expected '(' after function name")
        self._skip_separators()
        params = []
        if not self._check("RPAREN"):
            params.append(self._consume("IDENTIFIER", "Expected parameter name").value)
            while True:
                self._skip_separators()
                if not self._match("COMMA"):
                    break
                self._skip_separators()
                if self._check("RPAREN"):
                    break
                params.append(self._consume("IDENTIFIER", "Expected parameter name").value)
        self._skip_separators()
        self._consume("RPAREN", "Expected ')' after parameters")
        return Function(name, params, self._block())

    def _if_statement(self):
        condition = self._expression()
        then_branch = self._block()
        else_branch = []
        if self._match("NAH"):
            else_branch = self._block()
        return If(condition, then_branch, else_branch)

    def _while_statement(self):
        condition = self._expression()
        return While(condition, self._block())

    def _block(self):
        self._consume("LBRACE", "Expected '{' to start a block")
        statements = []
        self._skip_separators()
        while not self._check("RBRACE") and not self._check("EOF"):
            statements.append(self._statement())
            self._skip_separators()
        self._consume("RBRACE", "Expected '}' after block")
        return statements

    def _expression(self):
        return self._or()

    def _or(self):
        expr = self._and()
        while self._match("OP", "||"):
            expr = Binary("||", expr, self._and())
        return expr

    def _and(self):
        expr = self._equality()
        while self._match("OP", "&&"):
            expr = Binary("&&", expr, self._equality())
        return expr

    def _equality(self):
        expr = self._comparison()
        while self._check("OP") and self._peek().value in ("==", "!="):
            operator = self._advance().value
            expr = Binary(operator, expr, self._comparison())
        return expr

    def _comparison(self):
        expr = self._term()
        while self._check("OP") and self._peek().value in ("<", ">", "<=", ">="):
            operator = self._advance().value
            expr = Binary(operator, expr, self._term())
        return expr

    def _term(self):
        expr = self._factor()
        while self._check("PLUS") or self._check("MINUS"):
            operator = self._advance().value
            expr = Binary(operator, expr, self._factor())
        return expr

    def _factor(self):
        expr = self._unary()
        while self._check("STAR") or self._check("SLASH") or self._check("PERCENT"):
            operator = self._advance().value
            expr = Binary(operator, expr, self._unary())
        return expr

    def _unary(self):
        if self._check("OP") and self._peek().value in ("!", "-"):
            operator = self._advance().value
            return Unary(operator, self._unary())
        if self._match("MINUS"):
            return Unary("-", self._unary())
        return self._call()

    def _call(self):
        expr = self._primary()
        while True:
            if self._match("LPAREN"):
                arguments = []
                self._skip_separators()
                if not self._check("RPAREN"):
                    arguments.append(self._expression())
                    while True:
                        self._skip_separators()
                        if not self._match("COMMA"):
                            break
                        self._skip_separators()
                        if self._check("RPAREN"):
                            break
                        arguments.append(self._expression())
                self._skip_separators()
                self._consume("RPAREN", "Expected ')' after arguments")
                expr = Call(expr, arguments)
            elif self._match("DOT"):
                key = self._consume("IDENTIFIER", "Expected property name after '.'").value
                expr = Get(expr, Literal(key))
            elif self._match("LBRACKET"):
                self._skip_separators()
                key = self._expression()
                self._skip_separators()
                self._consume("RBRACKET", "Expected ']' after index")
                expr = Get(expr, key)
            else:
                break
        return expr

    def _primary(self):
        if self._match("NUMBER"):
            return Literal(self._previous().value)
        if self._match("STRING"):
            return Literal(self._previous().value)
        if self._match("BASED"):
            return Literal(True)
        if self._match("CRINGE"):
            return Literal(False)
        if self._match("GHOST"):
            return Literal(None)
        if self._match("IDENTIFIER"):
            return Variable(self._previous().value)
        if self._match("LPAREN"):
            expr = self._expression()
            self._consume("RPAREN", "Expected ')' after expression")
            return expr
        if self._match("LBRACKET"):
            items = []
            self._skip_separators()
            if not self._check("RBRACKET"):
                items.append(self._expression())
                while True:
                    self._skip_separators()
                    if not self._match("COMMA"):
                        break
                    self._skip_separators()
                    if self._check("RBRACKET"):
                        break
                    items.append(self._expression())
            self._skip_separators()
            self._consume("RBRACKET", "Expected ']' after list")
            return ListExpression(items)
        if self._match("LBRACE"):
            entries = []
            self._skip_separators()
            if not self._check("RBRACE"):
                while True:
                    key = self._consume("IDENTIFIER", "Expected object key").value
                    self._consume("COLON", "Expected ':' after object key")
                    entries.append((key, self._expression()))
                    self._skip_separators()
                    if not self._match("COMMA"):
                        break
                    self._skip_separators()
                    if self._check("RBRACE"):
                        break
            self._skip_separators()
            self._consume("RBRACE", "Expected '}' after object")
            return MapExpression(entries)
        raise ParseError(f"Unexpected token {self._peek().value!r} at line {self._peek().line}, column {self._peek().column}")

    def _skip_separators(self):
        while self._match("NEWLINE") or self._match("SEMICOLON"):
            pass

    def _match(self, kind, value=None):
        if self._check(kind) and (value is None or self._peek().value == value):
            self._advance()
            return True
        return False

    def _check(self, kind):
        return self._peek().kind == kind

    def _advance(self):
        if not self._check("EOF"):
            self.index += 1
        return self.tokens[self.index - 1]

    def _previous(self):
        return self.tokens[self.index - 1]

    def _peek(self):
        return self.tokens[self.index]

    def _consume(self, kind, message):
        if self._check(kind):
            return self._advance()
        token = self._peek()
        raise ParseError(f"{message} at line {token.line}, column {token.column}")


def parse(source):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()
