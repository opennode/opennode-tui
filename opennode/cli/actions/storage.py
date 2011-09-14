
import os

from opennode.cli.config import c, cs

def list_pools():
    """List existing storage pools"""
    return os.listdir(c('general', 'templates-folder'))

def set_default_pool(name):
    """Set default storage pool"""
    cs('general', 'default-storage-pool', name)

