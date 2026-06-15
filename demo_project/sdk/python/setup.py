"""TenGod Python SDK - 十神架构 HTTP API 客户端"""

from setuptools import find_packages, setup

setup(
    name="tengod-client",
    version="2.1.0",
    description="十神架构 Python SDK — 中华文明数字永生体 HTTP API 客户端",
    long_description=open("tengod_client/__init__.py", encoding="utf-8")
    .read()
    .split('"""')[1],
    author="TenGod Team",
    packages=find_packages(),
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="tengod, ai, knowledge-graph, oracle, chinese-civilization",
    url="https://github.com/tengod/tengod-client",
)
