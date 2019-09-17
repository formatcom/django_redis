import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django_redis',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description='',
    long_description=README,
    url='https://github.com/formatcom/django_redis',
    author='Vinicio Valbuena',
    author_email='vinicio.valbuena89@gmail.com',
)
