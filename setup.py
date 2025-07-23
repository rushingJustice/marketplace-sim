from setuptools import setup, find_packages

setup(
    name="marketplace-sim",
    version="0.1.0",
    description="Marketplace interference simulation for A/B testing bias analysis",
    author="Marketplace Research Team",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.3.0", 
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "scipy>=1.7.0",
        "tqdm>=4.60.0",
        "jupyter>=1.0.0",
        "pytest>=6.0.0"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "marketplace-sim=market_sim.__main__:main",
        ],
    },
)