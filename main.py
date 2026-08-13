"""Entrypoint que Vercel detecta por convencion (nombre reservado: main.py
en la raiz). La app real vive en backend/main.py; aqui solo se reexporta,
para no mover el codigo fuera de la arquitectura por capas documentada.
"""
from backend.main import app  # noqa: F401
