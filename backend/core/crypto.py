"""Cifrado de datos sensibles en reposo (RNF-02: "los datos sensibles debera
encriptarlos con AES-256 cuando estan guardados").

Esto es una capa distinta de `core/security.py`:
  - security.py protege CONTRASENAS: se verifican por comparacion (bcrypt),
    nunca se necesita recuperar el valor original.
  - crypto.py protege DATOS SENSIBLES que si hace falta leer de vuelta
    (el email, para mostrarlo o enviar notificaciones). AES-256 es reversible
    por diseno; bcrypt no lo es.

El problema que resuelve el "indice ciego"
-------------------------------------------
AES-GCM usa un nonce aleatorio en cada cifrado, asi que la MISMA cadena
("admin@hotel.com") produce un texto cifrado DISTINTO cada vez. Eso es
deseable para la confidencialidad, pero rompe la busqueda: no se puede hacer
`WHERE email_cifrado = ?` para el login, porque el valor guardado nunca es
igual al que se querria buscar.

La solucion estandar es un "indice ciego" (blind index): ademas del valor
cifrado, se guarda un HMAC-SHA256 determinista del email normalizado. El
mismo email siempre produce el mismo HMAC, así que ese campo si sirve para
`WHERE email_hash = ?` con busqueda O(log n) por indice. El HMAC no es
reversible (no se puede recuperar el email a partir del hash), asi que no
reintroduce el problema que AES-256 vino a resolver.
"""
import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.core.config import settings

# Tamano de nonce recomendado para AES-GCM (96 bits).
_TAMANO_NONCE = 12


def _clave_cifrado() -> bytes:
    """Clave AES-256 (32 bytes), derivada de SECRET_KEY con un contexto propio.

    No se reutiliza SECRET_KEY tal cual: esa clave firma los JWT. Usar la
    misma clave para dos propositos distintos (firma y cifrado) es una mala
    practica criptografica — si una se compromete, compromete a la otra.
    SHA-256 con un separador de contexto deriva una clave distinta a partir
    del mismo secreto, sin pedirle al usuario una variable de entorno mas.
    """
    material = f"{settings.SECRET_KEY}:cifrado-datos-sensibles".encode("utf-8")
    return hashlib.sha256(material).digest()


def _clave_indice() -> bytes:
    """Clave del HMAC del indice ciego. Distinta de la clave de cifrado por
    la misma razon: cada mecanismo criptografico con su propia clave."""
    material = f"{settings.SECRET_KEY}:indice-busqueda".encode("utf-8")
    return hashlib.sha256(material).digest()


def cifrar(texto_plano: str) -> str:
    """AES-256-GCM. Devuelve base64(nonce + texto_cifrado + tag_autenticacion)."""
    aesgcm = AESGCM(_clave_cifrado())
    nonce = os.urandom(_TAMANO_NONCE)
    cifrado = aesgcm.encrypt(nonce, texto_plano.encode("utf-8"), None)
    return base64.b64encode(nonce + cifrado).decode("ascii")


def descifrar(token: str) -> str:
    """Inverso de `cifrar`. Lanza ValueError si el dato fue alterado: GCM
    verifica integridad ademas de confidencialidad."""
    crudo = base64.b64decode(token)
    nonce, cifrado = crudo[:_TAMANO_NONCE], crudo[_TAMANO_NONCE:]
    aesgcm = AESGCM(_clave_cifrado())
    return aesgcm.decrypt(nonce, cifrado, None).decode("utf-8")


def indice_busqueda(texto_plano: str) -> str:
    """HMAC-SHA256 determinista, para localizar filas sin descifrar la tabla
    entera. Normaliza a minusculas/sin espacios: sin esto, "Admin@Hotel.com"
    y "admin@hotel.com" generarian hashes distintos y el login fallaria por
    diferencias de mayusculas que a un humano le resultan iguales."""
    normalizado = texto_plano.strip().lower().encode("utf-8")
    return hmac.new(_clave_indice(), normalizado, hashlib.sha256).hexdigest()
