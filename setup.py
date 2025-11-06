"""
Setup configuration for ProDuckt.
"""

from setuptools import setup, find_packages

setup(
    name="produck",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi==0.109.0",
        "uvicorn[standard]==0.27.0",
        "sqlalchemy==2.0.25",
        "alembic==1.13.1",
        "psycopg2-binary==2.9.9",
        "bcrypt==4.1.2",
        "pydantic==2.5.3",
        "pydantic-settings==2.1.0",
        "anthropic==0.18.1",
        "redis==5.0.1",
        "python-dotenv==1.0.0",
    ],
)
