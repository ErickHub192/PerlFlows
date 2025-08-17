"""
Fake Data Registry System
Sistema modular para generar datos fake realistas para dryrun de workflows
"""

from .registry import fake_data_registry, register_fake_generator
from .generators import *  # Importa todos los generadores

__all__ = ['fake_data_registry', 'register_fake_generator']