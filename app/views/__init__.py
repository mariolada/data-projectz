"""
Módulos de vistas para el dashboard.
Cada vista es una función que recibe los DataFrames necesarios.
"""
from views.modo_hoy import render_modo_hoy
from views.semana import render_semana
from views.perfil import render_perfil
from views.entrenamiento import render_entrenamiento

__all__ = ['render_modo_hoy', 'render_semana', 'render_perfil', 'render_entrenamiento']
