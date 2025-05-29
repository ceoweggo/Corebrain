"""
Installer configuration for Corebrain package.
"""

from setuptools import setup, find_packages

setup(
    name="corebrain",
    version="1.0.0",
    description="SDK for natural language ask to DB",
    author="Rubén Ayuso",
    author_email="ruben@globodain.com",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.23.0",
        "pymongo>=4.3.0",
        "psycopg2-binary>=2.9.5",
        "mysql-connector-python>=8.0.31",
        "sqlalchemy>=2.0.0",
        "cryptography>=39.0.0",
        "pydantic>=1.10.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "corebrain=corebrain.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)