from setuptools import setup, find_packages
import re
from pathlib import Path

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in frappe_sepa_export/__version__.py
version_file = Path(__file__).parent / "frappe_sepa_export" / "__version__.py"
version = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', version_file.read_text()).group(1)

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
