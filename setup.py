from setuptools import setup, find_packages

setup(
    name="telegram-hooker",
    version="1.0.0",
    author="@ASEQX12",
    description="Telegram voice call control tool",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pyrogram>=2.0.106",
        "py-tgcalls==2.2.0",
        "ntgcalls==2.2.5",
        "aiohttp>=3.8.0",
        "pyaes>=1.6.1",
    ],
)
