from setuptools import setup, find_packages
setup(
    name='klemco_cs',
    version='1.0.0',
    description='Klemco Customer Service Module',
    author='Klemco India',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['frappe'],
)
