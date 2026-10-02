"""Tiny synthetic fixtures and safe source loading; no supplied art is regenerated."""
import ast
import importlib
import importlib.util
from pathlib import Path
import sys
import types
import numpy as np
from PIL import Image, ImageDraw

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parents[1]
SOURCES = ROOT / 'skill_migration' / 'sources'
if not SOURCES.is_dir():
    SOURCES = SKILL / 'tests' / 'fixtures' / 'sources'
sys.path.insert(0, str(SKILL))


def core(name):
    return importlib.import_module('core.' + name)


def original(group, filename):
    name = '_original_' + group + '_' + filename.replace(' ', '_').replace('.', '_')
    spec = importlib.util.spec_from_file_location(name, SOURCES / group / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_functions(group, filename, names, globals_dict=None):
    """Only requested function definitions execute, never asset-loading demo code."""
    path = SOURCES / group / filename
    tree = ast.parse(path.read_text())
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    if {n.name for n in selected} != set(names):
        raise AssertionError('Missing original function')
    module = types.ModuleType('_selected_source')
    module.__dict__.update(globals_dict or {})
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), module.__dict__)
    return module


def sprite(size=(64, 64), box=(20, 16, 40, 48), color=(220, 40, 30, 255)):
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle(box, fill=color)
    return im


def project(matrix, point):
    value = matrix @ np.array([*point, 1.0])
    return value[:2] / value[2]


def tree():
    return {
        'root': {'pivot': [24, 24], 'parent': None, 'z': 0, 'anchors': {'joint': [28, 24]}},
        'arm': {'pivot': [28, 24], 'parent': 'root', 'z': 1, 'anchors': {'joint': [28, 24], 'tip': [40, 30]}},
        'claw': {'pivot': [40, 30], 'parent': 'arm', 'z': 2, 'anchors': {'knuckle': [40, 30]}},
        'catch': {'pivot': [48, 40], 'parent': None, 'z': 3, 'anchors': {'contact': [40, 30]}},
    }
