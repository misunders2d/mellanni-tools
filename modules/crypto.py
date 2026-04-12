"""Symmetric encryption helper using Fernet.

Keeps sensitive strings (OTP secrets, API tokens) encrypted at rest in Supabase.
The encryption key lives in .streamlit/secrets.toml and never leaves the server.
"""

import streamlit as st
from cryptography.fernet import Fernet


@st.cache_resource
def _get_fernet() -> Fernet:
    key = st.secrets["encryption_key"]
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a string, return base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
