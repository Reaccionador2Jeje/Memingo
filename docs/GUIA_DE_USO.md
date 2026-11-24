# Guía de uso de Memingo

**Manual para Memingo 0.2**  
Esta guía describe el lenguaje y los comandos documentados en el repositorio. Si un comando cambia entre versiones, consulta primero `memingo --help`.

## 1. ¿Qué es Memingo?

Memingo es un ecosistema de programación inspirado en memes. Sus archivos de código usan la extensión `.mgo`. El proyecto incluye un intérprete, herramientas de proyecto, administrador de paquetes `mgoa`, servidor HTTP, herramientas de formato y diagnóstico, LSP e IDE web.

El runtime oficial requiere **Python 3.10 o posterior**. No necesitas instalar dependencias con `pip` para usar el instalador oficial.

## 2. Instalar

### Linux y macOS

Desde una copia del repositorio:

```bash
chmod +x scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
mgoa --version
```

Si descargaste el instalador publicado, entra en la carpeta donde está `install.sh` y ejecuta:

```bash
chmod +x install.sh
sh ./install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
mgoa --version
```

La ubicación predeterminada de los comandos es `~/.local/bin`. Si la terminal no encuentra `memingo`, comprueba que esa carpeta esté en tu variable `PATH`.

### Windows

Abre PowerShell en la carpeta del repositorio y ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```

Abre una terminal nueva y comprueba:

```powershell
memingo --version
mgoa --version
```

El instalador coloca Memingo en `%LOCALAPPDATA%\Memingo` y agrega su carpeta `bin` al PATH del usuario.

## 3. Tu primer programa

Crea un archivo llamado `main.mgo`:

```mgo
# Mi primer programa Memingo
vibe nombre = "Memingo"
spill "Hola desde " + nombre + "!"

vibe numero = 6
when numero > 3 {
    spill "Esto es based"
} nah {
    spill "Eso es cringe"
}
```

Ejecútalo desde la carpeta que contiene el archivo:

```bash
memingo run main.mgo
```

Si todavía no instalaste el comando nativo, desde la raíz del repositorio puedes usar:

```bash
python3 -m memingo run main.mgo
```

Salida esperada:

```text
Hola desde Memingo!
Esto es based
```

## 4. Sintaxis esencial

### Variables y valores

La palabra clave `vibe` declara una variable:

```mgo
vibe edad = 12
vibe nombre = "Cris"
vibe activo = based
vibe desactivado = cringe
vibe sin_valor = ghost
vibe numeros = [1, 2, 3]
vibe perfil = {nombre: "Ana", rol: "builder"}
```

Los tipos principales son números (`whole`), texto (`caption`), listas (`party`), booleanos (`based` y `cringe`), objetos y `ghost` (ausencia de valor).

### Mostrar información

Usa `spill`:

```mgo
spill "Hola"
spill 2 + 2
```

### Condiciones

Usa `when` y, opcionalmente, `nah`:

```mgo
vibe puntos = 10
when puntos >= 10 {
    spill "Nivel desbloqueado"
} nah {
    spill "Sigue intentando"
}
```

### Bucles

Usa `grind` mientras la condición sea verdadera:

```mgo
vibe i = 1
grind i <= 3 {
    spill i
    i = i + 1
}
```

### Funciones

Una función se declara con `ritual` y devuelve un valor con `drop`:

```mgo
ritual doble(numero) {
    drop numero * 2
}

spill doble(8)
```

`drop` termina inmediatamente la función que lo contiene. También puede usarse en el nivel superior para detener el programa y devolver un valor.

### Operadores

- Matemáticos: `+ - * / %`
- Comparación: `< > <= >=`
- Igualdad: `== !=`
- Lógicos: `&& || !`

El operador `+` también concatena texto.

## 5. Listas, objetos y biblioteca estándar

```mgo
vibe perfil = {nombre: "Ana", rol: "builder"}
vibe tareas = ["crear", "probar", "publicar"]

spill perfil.nombre
spill perfil["rol"]
spill headcount(tareas)

push(tareas, "documentar")
set_value(perfil, "estado", "based")
spill json_stringify(perfil)
```

Funciones útiles:

| Área | Funciones |
| --- | --- |
| Colecciones | `headcount`, `keys`, `values`, `push`, `append`, `sort`, `reverse`, `unique`, `sum`, `min`, `max`, `slice` |
| Texto | `upper`, `lower`, `trim`, `split`, `join`, `replace`, `contains`, `repeat`, `lines`, `meme_case` |
| Números | `abs`, `floor`, `ceil`, `round`, `clamp`, `parse_int`, `parse_float`, `random`, `random_int`, `range` |
| Funciones | `map`, `filter`, `reduce` |
| Datos y red | `json_parse`, `json_stringify`, `env`, `now`, `sleep`, `http_get`, `http_post` |
| Archivos | `read_file`, `write_file`, `file_exists`, `list_files` |

Ejemplo de transformación de listas:

```mgo
ritual doble(n) {
    drop n * 2
}

spill map([1, 2, 3], doble)
spill sort([3, 1, 2])
```

Los helpers de archivos están restringidos al directorio del proyecto. No aceptan rutas absolutas ni rutas que escapen del proyecto mediante `..`.

## 6. Crear y gestionar proyectos

Para iniciar un proyecto:

```bash
memingo init mi-app --name mi-app
cd mi-app
memingo run
```

Los comandos conscientes del proyecto pueden crear los archivos de inicio y el manifiesto `memingo.toml` cuando faltan. Un manifiesto existente no se sobrescribe. Para crear solamente el manifiesto que falta:

```bash
memingo manifest
```

Comandos principales documentados:

| Comando | Uso |
| --- | --- |
| `memingo init NOMBRE` | Crear un proyecto |
| `memingo run [ARCHIVO]` | Ejecutar código |
| `memingo eval 'CODIGO'` | Evaluar una expresión o fragmento |
| `memingo check RUTA` | Comprobar código |
| `memingo dev` | Flujo de desarrollo |
| `memingo test` | Ejecutar pruebas del proyecto |
| `memingo build` | Ejecutar el flujo de construcción del proyecto |
| `memingo fmt RUTA` | Formatear archivos |
| `memingo serve [CARPETA]` | Servir archivos estáticos |
| `memingo info` | Mostrar información del proyecto |
| `memingo deps` | Consultar dependencias |
| `memingo clean` | Limpiar artefactos del proyecto |
| `memingo stats` | Mostrar estadísticas |
| `memingo doctor` | Diagnosticar la instalación |
| `memingo update-self` | Actualizar la instalación |
| `memingo completion` | Generar autocompletado de shell |
| `memingo lsp --stdio` | Iniciar el servidor LSP |
| `memingo ide` | Iniciar el IDE web |

Para conocer opciones y argumentos exactos de tu versión:

```bash
memingo --help
memingo run --help
memingo --version
```

## 7. Paquetes con MGOA

MGOA es el administrador de paquetes de Memingo. Ejemplos:

```bash
mgoa search
mgoa info hello-memes
mgoa list
mgoa add hello-memes
mgoa install
mgoa update
mgoa remove hello-memes
```

También admite directorios locales, archivos ZIP y URL HTTP(S) de archivos de paquetes:

```bash
mgoa add ./mi-paquete
mgoa add ./mi-paquete.zip
```

En un programa, importa un paquete instalado con `borrow`:

```mgo
borrow "hello-memes"
greet("Equipo")
```

MGOA registra fuentes y checksums en `memingo.lock.json` para hacer las instalaciones reproducibles. La extracción ZIP incluye protecciones contra rutas que intenten salir del directorio de destino y los paquetes se verifican mediante SHA-256.

Para publicar un paquete se usa `mgoa publish .`. La publicación requiere configurar `MGOA_PUBLISH_TOKEN` con permiso de escritura de contenidos en el repositorio Memingo. **No compartas ese token ni lo escribas en código público.**

## 8. Crear una API HTTP

Ejemplo de servidor nativo en `.mgo`:

```mgo
vibe app = api()

ritual inicio(request) {
    drop {nombre: "Memingo API", estado: "based"}
}

ritual saludo(request) {
    drop {mensaje: "Hola " + request.params.nombre}
}

api_get(app, "/", inicio)
api_get(app, "/hola/<nombre>", saludo)
api_listen(app)
```

Inícialo desde la raíz del proyecto:

```bash
memingo api servidor.mgo
```

Por defecto escucha en `127.0.0.1:8000`. Puedes visitar `http://127.0.0.1:8000/` desde el mismo dispositivo. El servidor también admite rutas POST, PUT, PATCH y DELETE, middleware y respuestas JSON, texto, HTML y redirecciones. Consulta [SERVER.md](SERVER.md) para rutas, formularios, cargas de archivos y límites de seguridad.

## 9. IDE web y editor

El IDE web se inicia con:

```bash
memingo ide
memingo ide --port 8080
```

La integración requiere instalar o enlazar una vez el proyecto [Memingo-IDE](https://github.com/Reaccionador2Jeje/Memingo-IDE) mediante `npm link`. El servidor web usa módulos integrados de Node.js y se enlaza a localhost. Consulta la [guía del IDE web](https://github.com/Reaccionador2Jeje/Memingo-IDE/blob/main/docs/WEB.md).

El servidor LSP se inicia con:

```bash
memingo lsp --stdio
```

Incluye diagnósticos del parser, autocompletado, documentación al pasar el cursor, ir a definición, referencias, renombrado local seguro y símbolos del documento.

## 10. IA integrada

Memingo incluye una API de entrenamiento CPU para redes neuronales densas pequeñas:

```mgo
vibe model = ai.create({
    name: "MiModelo",
    layers: [2, 4, 1],
    activation: "sigmoid"
})

vibe datos = ai.dataset(
    [[0, 0], [0, 1], [1, 0], [1, 1]],
    [[0], [1], [1], [0]]
)

vibe informe = ai.train(model, datos, {
    epochs: 1000,
    learning_rate: 0.3,
    batch_size: 2,
    shuffle: based
})

spill informe.loss
spill ai.predict(model, [0, 1])
```

El motor inicial es CPU y está pensado para aprendizaje y modelos pequeños. No ofrece actualmente aceleración GPU ni entrenamiento de modelos grandes de lenguaje.

## 11. Diagnóstico y pruebas

Si algo no funciona:

```bash
memingo --version
memingo doctor
memingo --help
```

Desde el repositorio también puedes ejecutar la suite:

```bash
python3 -m unittest discover -s tests -v
memingo test
```

Para depurar un archivo con una traza de sentencias:

```bash
memingo debug main.mgo
```

La traza JSON se emite con el prefijo `MEMINGO_DEBUG:`. Puedes marcar líneas concretas con `--breakpoints 3,8`.

## 12. Ejemplos y documentación

- [Referencia completa del lenguaje](../LANGUAGE.md)
- [Ejemplos de código](../examples/)
- [Servidor HTTP](SERVER.md)
- [Publicación de paquetes MGOA](MGOA_PUBLISHING.md)
- [Módulos locales MGOA](MGOA_LOCAL_MODULES.md)
- [Servidor LSP](LANGUAGE_SERVER.md)
- [Repositorio de Memingo](https://github.com/Reaccionador2Jeje/Memingo)
- [Sitio oficial](https://reaccionador2Jeje.github.io/Memingo)

---

**Memingo 0.2 — Programa con estilo. Construye en serio.**


---

# Memingo User Guide (English)

**Manual for Memingo 0.2**  
This guide covers the language and commands documented in the repository. If a command changes between versions, check `memingo --help` first.

## 1. What is Memingo?

Memingo is a meme-inspired programming ecosystem. Its source files use the `.mgo` extension. The project includes an interpreter, project tools, the `mgoa` package manager, an HTTP server, formatting and diagnostics tools, an LSP server, and a web IDE.

The official runtime requires **Python 3.10 or newer**. You do not need to install dependencies with `pip` when using the official installer.

## 2. Installation

### Linux and macOS

From a repository checkout:

```bash
chmod +x scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
mgoa --version
```

If you downloaded the published installer, enter the directory containing `install.sh` and run:

```bash
chmod +x install.sh
sh ./install.sh
export PATH="$HOME/.local/bin:$PATH"
memingo --version
mgoa --version
```

The default command location is `~/.local/bin`. If your shell cannot find `memingo`, make sure that directory is included in your `PATH`.

### Windows

Open PowerShell in the repository directory and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install.ps1
```

Open a new terminal and verify the installation:

```powershell
memingo --version
mgoa --version
```

The installer places Memingo in `%LOCALAPPDATA%\Memingo` and adds its `bin` directory to the user's PATH.

## 3. Your first program

Create a file named `main.mgo`:

```mgo
# My first Memingo program
vibe name = "Memingo"
spill "Hello from " + name + "!"

vibe number = 6
when number > 3 {
    spill "That's based"
} nah {
    spill "That's cringe"
}
```

Run it from the directory containing the file:

```bash
memingo run main.mgo
```

If you have not installed the native command yet, run this from the repository root:

```bash
python3 -m memingo run main.mgo
```

Expected output:

```text
Hello from Memingo!
That's based
```

## 4. Essential syntax

### Variables and values

Use the `vibe` keyword to declare a variable:

```mgo
vibe age = 12
vibe name = "Cris"
vibe active = based
vibe inactive = cringe
vibe missing = ghost
vibe numbers = [1, 2, 3]
vibe profile = {name: "Ana", role: "builder"}
```

The main value types are numbers (`whole`), text (`caption`), lists (`party`), booleans (`based` and `cringe`), objects, and `ghost` (the absence of a value).

### Printing output

Use `spill`:

```mgo
spill "Hello"
spill 2 + 2
```

### Conditions

Use `when` and optionally `nah`:

```mgo
vibe points = 10
when points >= 10 {
    spill "Level unlocked"
} nah {
    spill "Keep trying"
}
```

### Loops

Use `grind` to repeat while a condition is true:

```mgo
vibe i = 1
grind i <= 3 {
    spill i
    i = i + 1
}
```

### Functions

Declare a function with `ritual` and return a value with `drop`:

```mgo
ritual double(number) {
    drop number * 2
}

spill double(8)
```

`drop` immediately exits the function containing it. At the top level, it can also stop the program and return a value.

### Operators

- Arithmetic: `+ - * / %`
- Comparison: `< > <= >=`
- Equality: `== !=`
- Logical: `&& || !`

The `+` operator also concatenates text.

## 5. Lists, objects, and the standard library

```mgo
vibe profile = {name: "Ana", role: "builder"}
vibe tasks = ["create", "test", "publish"]

spill profile.name
spill profile["role"]
spill headcount(tasks)

push(tasks, "document")
set_value(profile, "status", "based")
spill json_stringify(profile)
```

Useful functions:

| Area | Functions |
| --- | --- |
| Collections | `headcount`, `keys`, `values`, `push`, `append`, `sort`, `reverse`, `unique`, `sum`, `min`, `max`, `slice` |
| Text | `upper`, `lower`, `trim`, `split`, `join`, `replace`, `contains`, `repeat`, `lines`, `meme_case` |
| Numbers | `abs`, `floor`, `ceil`, `round`, `clamp`, `parse_int`, `parse_float`, `random`, `random_int`, `range` |
| Functions | `map`, `filter`, `reduce` |
| Data and networking | `json_parse`, `json_stringify`, `env`, `now`, `sleep`, `http_get`, `http_post` |
| Files | `read_file`, `write_file`, `file_exists`, `list_files` |

Example: transform a list:

```mgo
ritual double(n) {
    drop n * 2
}

spill map([1, 2, 3], double)
spill sort([3, 1, 2])
```

File helpers are restricted to the project directory. They reject absolute paths and paths that attempt to escape the project using `..`.

## 6. Creating and managing projects

Create a project:

```bash
memingo init my-app --name my-app
cd my-app
memingo run
```

Project-aware commands can create starter files and the `memingo.toml` manifest when they are missing. An existing manifest is never overwritten. To create only the missing manifest:

```bash
memingo manifest
```

Main documented commands:

| Command | Purpose |
| --- | --- |
| `memingo init NAME` | Create a project |
| `memingo run [FILE]` | Run code |
| `memingo eval 'CODE'` | Evaluate an expression or snippet |
| `memingo check PATH` | Check code |
| `memingo dev` | Start the development workflow |
| `memingo test` | Run project tests |
| `memingo build` | Run the project build workflow |
| `memingo fmt PATH` | Format files |
| `memingo serve [DIRECTORY]` | Serve static files |
| `memingo info` | Show project information |
| `memingo deps` | Inspect dependencies |
| `memingo clean` | Clean project artifacts |
| `memingo stats` | Show statistics |
| `memingo doctor` | Diagnose the installation |
| `memingo update-self` | Update the installation |
| `memingo completion` | Generate shell completions |
| `memingo lsp --stdio` | Start the LSP server |
| `memingo ide` | Start the web IDE |

For the exact options supported by your installed version:

```bash
memingo --help
memingo run --help
memingo --version
```

## 7. Packages with MGOA

MGOA is Memingo's package manager. Common commands:

```bash
mgoa search
mgoa info hello-memes
mgoa list
mgoa add hello-memes
mgoa install
mgoa update
mgoa remove hello-memes
```

It also supports local directories, ZIP archives, and HTTP(S) package archive URLs:

```bash
mgoa add ./my-package
mgoa add ./my-package.zip
```

Import an installed package in a program with `borrow`:

```mgo
borrow "hello-memes"
greet("Team")
```

MGOA records package sources and checksums in `memingo.lock.json` to make installations reproducible. ZIP extraction protects against paths escaping the destination directory, and packages are verified with SHA-256.

Publish a package with `mgoa publish .`. Publishing requires an `MGOA_PUBLISH_TOKEN` with Contents: write permission on the Memingo repository. **Never share this token or commit it to public source code.**

## 8. Creating an HTTP API

Here is a native server in a `.mgo` file:

```mgo
vibe app = api()

ritual home(request) {
    drop {name: "Memingo API", status: "based"}
}

ritual greet(request) {
    drop {message: "Hello " + request.params.name}
}

api_get(app, "/", home)
api_get(app, "/hello/<name>", greet)
api_listen(app)
```

Start it from the project root:

```bash
memingo api server.mgo
```

By default, it listens on `127.0.0.1:8000`. Open `http://127.0.0.1:8000/` on the same device. The server also supports POST, PUT, PATCH, and DELETE routes, middleware, and JSON, text, HTML, and redirect responses. See [SERVER.md](SERVER.md) for routes, forms, file uploads, and security limits.

## 9. Web IDE and editor

Start the web IDE with:

```bash
memingo ide
memingo ide --port 8080
```

Integration requires linking the [Memingo-IDE project](https://github.com/Reaccionador2Jeje/Memingo-IDE) once with `npm link`. The web server uses built-in Node.js modules and binds to localhost. See the [web IDE guide](https://github.com/Reaccionador2Jeje/Memingo-IDE/blob/main/docs/WEB.md).

Start the LSP server with:

```bash
memingo lsp --stdio
```

It provides parser diagnostics, completions, hover documentation, go-to-definition, references, safe local symbol rename, and document symbols.

## 10. Built-in AI

Memingo includes a CPU training API for small dense neural networks:

```mgo
vibe model = ai.create({
    name: "MyModel",
    layers: [2, 4, 1],
    activation: "sigmoid"
})

vibe data = ai.dataset(
    [[0, 0], [0, 1], [1, 0], [1, 1]],
    [[0], [1], [1], [0]]
)

vibe report = ai.train(model, data, {
    epochs: 1000,
    learning_rate: 0.3,
    batch_size: 2,
    shuffle: based
})

spill report.loss
spill ai.predict(model, [0, 1])
```

The initial engine runs on the CPU and is intended for learning and small models. It currently does not provide GPU acceleration or large language model training.

## 11. Troubleshooting and tests

If something does not work, check:

```bash
memingo --version
memingo doctor
memingo --help
```

From a repository checkout, you can also run the test suite:

```bash
python3 -m unittest discover -s tests -v
memingo test
```

Debug a file with a statement trace:

```bash
memingo debug main.mgo
```

The JSON trace is emitted with the `MEMINGO_DEBUG:` prefix. You can mark specific lines with `--breakpoints 3,8`.

## 12. Examples and documentation

- [Complete language reference](../LANGUAGE.md)
- [Code examples](../examples/)
- [HTTP server](SERVER.md)
- [MGOA package publishing](MGOA_PUBLISHING.md)
- [MGOA local modules](MGOA_LOCAL_MODULES.md)
- [LSP server](LANGUAGE_SERVER.md)
- [Memingo repository](https://github.com/Reaccionador2Jeje/Memingo)
- [Official website](https://reaccionador2Jeje.github.io/Memingo)

---

**Memingo 0.2 — Code with style. Build for real.**
