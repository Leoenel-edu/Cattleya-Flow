"""Punto de entrada para el runtime de Python de Vercel (@vercel/python).

Vercel publica como funcion serverless cualquier archivo dentro de api/ que
exponga un objeto ASGI. La aplicacion real vive en backend/main.py; este
archivo solo la reexporta (ver vercel.json, que enruta todo el trafico aqui).
"""
from backend.main import app  # noqa: F401
