from setuptools import setup, find_packages
from setuptools import setup
#from Cython.Build import cythonize

setup(
    name='messageix_canada',  # Consider changing the name to avoid hyphens
    version='0.1.0',
    description='An Open Source Integrated Assessment Model for Canada',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(include=['MESSAGE_CA', 'MESSAGE_CA.*']),  # Adjust if needed
    install_requires=[
        'pandas',
        'numpy',
        'pycountry',
        'ixmp',
        'message_ix >= 3.4.0',
        'pyam-iamc >= 0.6',
        'scipy',
        'toml',
        'ipykernel',
        'pytest',
        'click',
        'message-ix-models',
    ],
    entry_points={
        'console_scripts': [
            'message-canada=MESSAGE_CA:messagerun',  
        ],
    },
    extras_require={
        'extras': ['geotext', 'message-ix-models'],  # Optional dependencies
    },
    #ext_modules = cythonize("MESSAGE_CA.py"),
)
