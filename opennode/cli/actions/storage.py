
import os

from opennode.cli.config import c, cs

def list_pools():
    """List existing storage pools"""
    return os.listdir(c('general', 'templates-folder'))

def set_default_pool(name):
    """Set pool as a default one"""
    cs('general', 'default-template-pool', name)

