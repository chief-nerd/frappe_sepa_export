from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in frappe_sepa_export/__version__.py
from frappe_sepa_export.__version__ import __version__ as version

setup(
    name="frappe_sepa_export",
    version=version,
    description="Generate SEPA XML Payment Instruction files for Purchase Invoices",
    author="Mimirio",
    author_email="dev@mimirio.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
