# Instalar y publicar Memingo en Linux

Memingo distribuye paquetes nativos para distribuciones basadas en **APT** (paquete DEB) y **DNF** (paquete RPM). La publicación en AUR no forma parte del proyecto.

Sitio oficial: https://reaccionador2jeje.github.io/Memingo/

## Requisitos

- Debian o Ubuntu (o derivada) para las instrucciones APT.
- Fedora, RHEL o una distribución compatible con DNF para las instrucciones RPM.
- Python 3.10 o posterior. Los paquetes declaran esta dependencia y el gestor de paquetes la instala si está disponible en los repositorios de la distribución.
- Conexión a Internet para descargar el repositorio y sus paquetes.

Los paquetes instalan el runtime en `/usr/lib/memingo` y los comandos `memingo` y `mgoa` en `/usr/bin`.

## Debian y Ubuntu (APT)

Copia y ejecuta estos comandos en una terminal:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl

curl -fsSLo /tmp/memingo-archive-keyring.asc \
  https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
sudo install -D -m 0644 /tmp/memingo-archive-keyring.asc \
  /usr/share/keyrings/memingo-archive-keyring.asc

echo "deb [signed-by=/usr/share/keyrings/memingo-archive-keyring.asc] https://reaccionador2jeje.github.io/Memingo/linux/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/memingo.list

sudo apt-get update
sudo apt-get install memingo
```

Comprueba la instalación:

```bash
memingo --version
mgoa --version
apt-cache policy memingo
```

APT verifica la firma del repositorio usando exclusivamente la clave indicada en `signed-by`.

## Fedora y sistemas compatibles con DNF

Crea el archivo del repositorio:

```bash
sudo tee /etc/yum.repos.d/memingo.repo >/dev/null <<'EOF'
[memingo]
name=Memingo
baseurl=https://reaccionador2jeje.github.io/Memingo/linux/rpm
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
EOF
```

Instala Memingo:

```bash
sudo dnf makecache
sudo dnf install memingo
```

DNF puede pedir confirmación para importar la clave pública del repositorio. Comprueba que el origen mostrado sea el repositorio oficial de Memingo antes de aceptar.

Comprueba la instalación:

```bash
memingo --version
mgoa --version
dnf info memingo
```

La configuración activa tanto la verificación de firmas de los paquetes RPM (`gpgcheck=1`) como la verificación de metadatos del repositorio (`repo_gpgcheck=1`).

## Android (Termux)

Termux no usa los repositorios APT de Debian/Ubuntu ni los paquetes RPM de Fedora. Por eso, en Android se instala Memingo con el instalador compatible con Termux, que coloca los comandos dentro de `$PREFIX/bin`.

Instala los requisitos y descarga el proyecto:

```bash
pkg update
pkg install -y git python
git clone https://github.com/Reaccionador2Jeje/Memingo.git
cd Memingo
sh scripts/install.sh
hash -r
memingo --version
mgoa --version
```

El instalador detecta Termux automáticamente, utiliza el Python de Termux y evita modificar archivos de configuración del PATH porque `$PREFIX/bin` ya está incluido en el entorno. No ejecutes `apt install memingo` en Termux: ese paquete se publica para distribuciones Debian/Ubuntu, no para el repositorio de paquetes de Android.

Para actualizar, entra en la carpeta del repositorio y ejecuta:

```bash
git pull
sh scripts/install.sh
```

Para desinstalar desde Termux:

```bash
sh scripts/uninstall.sh
```

## Desinstalar

Debian/Ubuntu:

```bash
sudo apt-get remove memingo
sudo rm -f /etc/apt/sources.list.d/memingo.list
sudo rm -f /usr/share/keyrings/memingo-archive-keyring.asc
sudo apt-get update
```

Fedora/DNF:

```bash
sudo dnf remove memingo
sudo rm -f /etc/yum.repos.d/memingo.repo
sudo dnf clean all
```

La desinstalación del paquete no elimina los proyectos que hayas creado en tus carpetas personales.

## Solución de problemas

- **No se encuentra el paquete:** confirma que agregaste el repositorio correcto, que la URL de Pages responde y que ejecutaste `sudo apt-get update` o `sudo dnf makecache`.
- **Error de firma en APT:** vuelve a descargar la clave pública desde la URL oficial y comprueba que la entrada `signed-by` apunta al archivo instalado.
- **Error de firma en DNF:** confirma que `gpgcheck=1`, `repo_gpgcheck=1` y `gpgkey` están presentes en `/etc/yum.repos.d/memingo.repo`. No desactives la verificación de firmas para evitar el error.
- **Falta Python:** instala Python 3.10 o posterior desde los repositorios oficiales de tu distribución.
- **El comando no aparece:** abre una terminal nueva y ejecuta `command -v memingo` y `command -v mgoa`.

## URLs de los repositorios

- Página principal: https://reaccionador2jeje.github.io/Memingo/
- Clave pública: https://reaccionador2jeje.github.io/Memingo/linux/memingo.asc
- APT: https://reaccionador2jeje.github.io/Memingo/linux/apt/
- RPM/DNF: https://reaccionador2jeje.github.io/Memingo/linux/rpm/

## Compilar paquetes localmente

Desde la raíz del repositorio:

```bash
# Debian/Ubuntu: requiere dpkg-deb
python3 scripts/build-packages.py --only deb

# Fedora/RHEL: requiere rpmbuild (paquete rpm-build)
python3 scripts/build-packages.py --only rpm

# Ambos formatos
python3 scripts/build-packages.py
```

Los archivos se generan en `dist/`. Para crear los metadatos locales de ambos repositorios:

```bash
python3 scripts/build-linux-repositories.py
```

## Publicación automática en GitHub Pages

El workflow **Publish Linux Package Repositories** publica el directorio `site/` cuando se impulsa un tag `v*` o se ejecuta manualmente mediante `workflow_dispatch`.

Debe existir un entorno de GitHub Pages configurado para el repositorio y estos tres secretos de GitHub Actions:

- `MEMINGO_GPG_PRIVATE_KEY`: clave privada GPG codificada en Base64.
- `MEMINGO_GPG_KEY_ID`: ID o huella de la clave de firma.
- `MEMINGO_GPG_PASSPHRASE`: frase de contraseña de esa clave.

**Nunca** guardes la clave privada ni la frase de contraseña en el repositorio, en archivos publicados, en incidencias o en mensajes. Configura los valores únicamente en GitHub Actions Secrets. El workflow verifica las firmas APT, los paquetes RPM y los metadatos RPM antes de desplegar; si una verificación falla, la publicación se detiene.

Para publicar una versión mediante un tag, por ejemplo:

```bash
git tag v0.2.0
git push origin v0.2.0
```

La clave pública se publica como `site/linux/memingo.asc`. APT firma `InRelease` y `Release.gpg`; RPM firma cada paquete y `repomd.xml`.

## Vista previa local del sitio

```bash
cd site
python3 -m http.server 4173
```

Abre http://127.0.0.1:4173/ en el navegador.
