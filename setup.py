from setuptools import setup, find_packages

setup(
    name='messageix_canada',
    version='0.1.0',
    description='An Open Source Integrated Assessment Model for Canada',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(include=['MESSAGE_CA', 'MESSAGE_CA.*']),  # Adjust if needed
    install_requires=[
        'setuptools >= 64', # Address deprecation warning from pip
        'pandas',
        'numpy',
        'plotly',
        'pycountry',
        'ixmp',
        'message_ix >= 3.4.0',
        'pyam-iamc >= 0.6',
        'scipy',
        'toml',
        'ipykernel',
        'pytest',
        'click',
        'message-ix-models@git+https://github.com/criscfer/message-ix-models.git@main',
        'message-ix-models[report]',
    ],
    #dependency_links=["git+https://github.com/criscfer/message-ix-models.git@main"], 
    entry_points={
        'console_scripts': [
            'message-canada=MESSAGE_CA:messagerun',  
        ],
    },
    extras_require={
        'extras': ['geotext', 'message-ix-models'],  # Optional dependencies
    },
)