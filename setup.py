from setuptools import setup, find_packages

setup(
    name='MESSAGEix-Canada',
    version='1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',  # Add other dependencies as needed
    ],
    entry_points='''
        [console_scripts]
        message-canada=model_script:messagerun
    ''',
)