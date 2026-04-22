from setuptools import setup, find_packages

setup(
    name="dharampal",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "langchain",
        "langchain-openai",
        "langgraph",
        "customtkinter",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "dharampal=dharampal.cli:main",
        ]
    }
)
