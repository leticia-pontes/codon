#!/usr/bin/env python3
"""
Setup para instalação do compilador Codon.
Permite usar 'codon run <arquivo>' de qualquer diretório.
"""

from setuptools import setup, find_packages
import os

# Lê requirements.txt
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(req_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Lê README para descrição longa
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Compilador Codon - Linguagem educacional compilada para LLVM IR"

setup(
    name='codon-compiler',
    version='0.1.0',
    description='Compilador educacional Codon (LLVM IR)',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='Letícia Pontes',
    url='https://github.com/leticia-pontes/codon',

    # Pacotes Python a instalar
    packages=find_packages(exclude=['test', 'test.*', 'examples', 'docs', 'scripts', 'tools']),

    # Dependências
    install_requires=read_requirements(),
    python_requires='>=3.10',

    # Script de entrada (CLI)
    entry_points={
        'console_scripts': [
            'codon=codon:main',
        ],
    },

    # Arquivos adicionais
    include_package_data=True,

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Education',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
