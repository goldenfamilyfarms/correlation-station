"""Setup script for sense_common shared library"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sense-common",
    version="1.0.0",
    author="SEEFA Observability Team",
    author_email="observability@seefa.com",
    description="Shared library for SEEFA Sense applications (Palantir, Arda, Beorn)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/goldenfamilyfarms/correlation-station",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.10.0",
        "pydantic-settings>=2.7.0",
        "httpx>=0.25.0",
        "structlog>=23.2.0",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
        "opentelemetry-exporter-otlp-proto-http>=1.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "mypy>=1.7.0",
        ]
    },
)
