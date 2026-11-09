# Memingo para Arch Linux (AUR)

Este directorio contiene el `PKGBUILD` y los metadatos `.SRCINFO` del paquete Arch Linux.

## Construcción local

Desde la raíz del repositorio:

```bash
sudo pacman -S --needed base-devel git python-build python-installer python-setuptools python-wheel
cd packaging/arch
makepkg -si
```

El paquete instala Memingo y los comandos `memingo` y `mgoa` mediante los entry points definidos en `pyproject.toml`.

## Publicación en AUR

La publicación oficial requiere una cuenta AUR y acceso SSH configurado para esa cuenta. Después de revisar y probar el paquete, copia `PKGBUILD` y `.SRCINFO` a un clon del repositorio AUR llamado `memingo`, y publica los cambios allí. No se incluyen credenciales en este repositorio.

Para actualizar una versión, cambia `pkgver`, regenera `.SRCINFO` con `makepkg --printsrcinfo > .SRCINFO` y prueba `makepkg -si` antes de publicar.
