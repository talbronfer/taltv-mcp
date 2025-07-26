"""Setup script for the radarr-sonarr-mcp package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="radarr-sonarr-mcp",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastmcp>=0.4.1",
        "requests>=2.28.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "radarr-sonarr-mcp=radarr_sonarr_mcp.cli:main",
        ],
    },
    author="Berry",
    author_email="",
    description="Model Context Protocol server for Radarr and Sonarr",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
        ],
    },
)
