from setuptools import setup, find_packages

setup(
    name="admf-trader",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas",
        "numpy",
        "matplotlib",
        "pyyaml",
        "jsonschema",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-cov",
            "pytest-mock",
            "pytest-timeout",
            "pytest-xdist",
            "hypothesis",
        ],
    },
)
