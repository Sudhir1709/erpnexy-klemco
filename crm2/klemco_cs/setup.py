from setuptools import setup, find_packages

with open("klemco_cs/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "1.3.0"

setup(
    name="klemco_cs",
    version=version,
    description="Klemco Customer Service Module",
    author="Klemco India",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
