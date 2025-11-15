from setuptools import setup, find_packages
import os

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in frappe_sepa_export/__version__.py
version = "0.0.1"
version_file = os.path.join(
    os.path.dirname(__file__), "frappe_sepa_export", "__version__.py"
)
if os.path.exists(version_file):
    with open(version_file) as f:
        exec(f.read())
        version = locals().get("__version__", version)

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
