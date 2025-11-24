from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.MD").read_text(encoding='utf-8')

# Read requirements from requirements.txt
def parse_requirements(filename):
    """Load requirements from a pip requirements file."""
    with open(filename, 'r') as f:
        lines = f.read().splitlines()
    # Filter out comments and empty lines
    requirements = [line.strip() for line in lines
                   if line.strip() and not line.startswith('#')]
    return requirements

setup(
    name='loan-prediction-mlops',
    version='1.0.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='MLOps-enabled Loan Prediction Model with comprehensive monitoring and deployment',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/Loan-Prediction_MLOps',
    packages=find_packages(exclude=['tests*', 'docs*']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.11',
    install_requires=parse_requirements('requirements.txt'),
    extras_require={
        'dev': [
            'pytest>=7.4.2',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
    },
    include_package_data=True,
    package_data={
        'prediction_model': [
            'config/*.py',
            'processing/*.py',
            'trained_models/*.pkl',
        ],
    },
    keywords='mlops machine-learning loan-prediction xgboost lightgbm mlflow',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/Loan-Prediction_MLOps/issues',
        'Source': 'https://github.com/yourusername/Loan-Prediction_MLOps',
        'Documentation': 'https://github.com/yourusername/Loan-Prediction_MLOps#readme',
    },
)
