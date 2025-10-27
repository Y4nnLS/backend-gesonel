"""
Setup para a biblioteca de reconhecimento de emoções
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="emotion-recognition-lib",
    version="1.0.0",
    author="Felipe Franco Pinheiro",
    author_email="felipe@example.com",
    description="Biblioteca para reconhecimento de emoções em áudio",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/emotion-recognition-lib",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "librosa>=0.9.0",
        "tensorflow>=2.8.0",
        "scipy>=1.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
        ],
    },
    entry_points={
        "console_scripts": [
            "emotion-predict=emotion_recognition_lib.cli:main",
        ],
    },
)
