# Frappe App Architecture

This document outlines the modern Frappe app structure used in this project, based on best practices from successful Frappe v15+ applications.

## Modern Frappe App Structure (v15+)

### Key Architectural Decisions

1. **Use `pyproject.toml` instead of `setup.py`**
   - Modern Python packaging standard (PEP 517/518)
   - Uses `flit_core` as the build backend
   - Simpler configuration and better tooling support

2. **Module-based `hooks.py` location**
   - Place `hooks.py` inside the app module directory (e.g., `frappe_sepa_export/hooks.py`)
   - With `pyproject.toml`, Frappe reads hooks from the module, not the root
   - Root `hooks.py` can be kept for backward compatibility but is not required

3. **Version management**
   - Define `__version__` in both `__init__.py` and `__version__.py`
   - Use `dynamic = ["version"]` in `pyproject.toml` to read from `__init__.py`
   - No complex version parsing needed

4. **Build system**
   - Use empty `build.json` (`{}`) for apps without asset bundling needs
   - JavaScript files loaded directly via `hooks.py` configuration
   - No esbuild/webpack required for simple JS files

## File Structure

```
frappe_sepa_export/
├── pyproject.toml              # Modern Python package configuration
├── MANIFEST.in                 # CRITICAL: Specifies which files to include in package
├── requirements.txt            # Python dependencies
├── package.json                # Node.js metadata (minimal for Frappe apps)
├── README.md                   # Documentation
└── frappe_sepa_export/         # Main app module
    ├── __init__.py             # Module initialization with __version__
    ├── __version__.py          # Version definition
    ├── hooks.py                # Frappe hooks configuration (ONLY here, not in root)
    ├── public/                 # Static assets (included via MANIFEST.in)
    │   └── js/                 # JavaScript files
    │       ├── frappe_sepa_export.js
    │       └── purchase_invoice.js
    ├── config/                 # App configuration
    │   └── frappe_sepa_export.py
    ├── doctype/                # Custom DocTypes
    ├── install/                # Installation scripts
    └── utils.py                # Utility functions
```

**Note:** No `build.json` file is needed for simple apps. Omit it entirely.

## pyproject.toml Configuration

```toml
[project]
name = "frappe_sepa_export"
authors = [
    { name = "Mimirio", email = "dev@mimirio.com"}
]
description = "Generate SEPA XML Payment Instruction files for Purchase Invoices"
requires-python = ">=3.10"
readme = "README.md"
dynamic = ["version"]           # Read version from __init__.py
dependencies = [
    "beautifulsoup4>=4.9.0"
]

[build-system]
requires = ["flit_core >=3.4,<4"]
build-backend = "flit_core.buildapi"

[project.urls]
Homepage = "https://github.com/chief-nerd/frappe_sepa_export"
Repository = "https://github.com/chief-nerd/frappe_sepa_export.git"
```

## JavaScript Asset Loading

For Frappe v15+, there are two ways to load JavaScript:

### 1. Direct Loading (Recommended for Simple Apps)
Configure in `hooks.py`:

```python
# Global JS - loads on all pages
app_include_js = "/assets/frappe_sepa_export/js/frappe_sepa_export.js"

# DocType-specific JS - loads only for specific DocTypes
doctype_js = {
    "Purchase Invoice": "public/js/purchase_invoice.js"
}
```

**No `build.json` file needed!** Simply omit it entirely.

**Benefits:**
- No build process needed
- Files served directly
- Faster development
- Simpler debugging
- No esbuild errors

**Requirements:**
- JavaScript files must be included via `MANIFEST.in` (see Critical section above)
- Use `recursive-include your_app_name *.js` in MANIFEST.in

### 2. Bundled Loading (For Complex Apps)
If using ES6 imports, TypeScript, or complex bundling, create `public/build.json`:

```json
{
    "js/frappe_sepa_export.js": [
        "public/js/module1.js",
        "public/js/module2.js"
    ]
}
```

This requires esbuild to process the files during `bench build`.

**Note:** Most apps don't need bundling. Start without `build.json` and only add it if you have complex build requirements.

## Version Management

### __init__.py
```python
__version__ = "0.0.1"
```

### __version__.py
```python
__version__ = "0.0.1"
```

Both files should contain the same version. The `pyproject.toml` with `dynamic = ["version"]` will automatically read from `__init__.py`.

## Installation Process

1. **Get app:** `bench get-app frappe_sepa_export https://github.com/chief-nerd/frappe_sepa_export`
2. **Install app:** `bench install-app frappe_sepa_export`
3. **Build assets:** `bench build --app frappe_sepa_export` (if needed)

With the modern structure:
- `pip` uses `pyproject.toml` for installation
- `flit_core` builds the package
- Version is read dynamically from `__init__.py`
- Assets are either bundled (if `build.json` has content) or served directly (if empty)

## Migration from Old Structure

If migrating from `setup.py` based structure:

1. Create `pyproject.toml` with proper configuration
2. Move or copy `hooks.py` to module directory
3. Ensure `__version__` exists in both `__init__.py` and `__version__.py`
4. Remove `setup.py`
5. Simplify `build.json` (use `{}` if no bundling needed)
6. Update `.gitignore` to exclude build artifacts

## Best Practices

1. **MANIFEST.in is CRITICAL** - Always include a complete `MANIFEST.in` file listing all asset types (JS, CSS, HTML, JSON, etc.). This is the #1 cause of "paths[0] undefined" errors.
2. **No build.json needed** - For simple apps, omit `build.json` entirely (don't even create an empty one). JavaScript loads via `hooks.py`.
3. **Module hooks only** - With `pyproject.toml`, place `hooks.py` ONLY in the module directory, not in root. Root hooks can cause conflicts.
4. **Keep JavaScript simple** - Avoid complex bundling unless necessary. Direct loading is faster and simpler.
5. **Use semantic versioning** - Follow MAJOR.MINOR.PATCH format
6. **Minimize dependencies** - Only include what's truly needed
7. **Test installation early** - After creating `MANIFEST.in`, test `pip install -e .` immediately to catch packaging issues
8. **Type hints** - Use Python type annotations for better IDE support
9. **Documentation** - Keep README.md updated with installation and usage instructions

## References

Successful Frappe apps following this structure:
- [red_background](https://github.com/alyf-de/red_background) - Minimal app example
- [erpnext_pdf-on-submit](https://github.com/alyf-de/erpnext_pdf-on-submit) - Feature-rich app
- [frappe/hrms](https://github.com/frappe/hrms) - Large-scale official app

## Critical: MANIFEST.in Configuration

**This is the most common cause of installation failures with pyproject.toml apps!**

The `MANIFEST.in` file tells Python which files to include when packaging the app. Without it, the `public/` directory and JavaScript files won't be included in the installed package, causing Frappe's esbuild to fail with:

```
TypeError [ERR_INVALID_ARG_TYPE]: The "paths[0]" argument must be of type string. Received undefined
```

### Required MANIFEST.in

```manifest
include MANIFEST.in
include requirements.txt
include *.json
include *.md
include *.py
include *.txt
recursive-include frappe_sepa_export *.css
recursive-include frappe_sepa_export *.csv
recursive-include frappe_sepa_export *.html
recursive-include frappe_sepa_export *.ico
recursive-include frappe_sepa_export *.js
recursive-include frappe_sepa_export *.json
recursive-include frappe_sepa_export *.md
recursive-include frappe_sepa_export *.png
recursive-include frappe_sepa_export *.svg
recursive-include frappe_sepa_export *.txt
recursive-include frappe_sepa_export *.py
recursive-exclude frappe_sepa_export *.pyc
```

**Key points:**
- Replace `frappe_sepa_export` with your app name
- Include all file types used in your app (JS, CSS, HTML, JSON, etc.)
- The `*.js` inclusion is critical for JavaScript files in `public/js/`
- Without this, pip installs the Python code but not the static assets

## Troubleshooting

### TypeError: paths[0] must be of type string. Received undefined
**Root Cause:** The `MANIFEST.in` file is missing or incomplete, so the `public/` directory isn't included in the pip-installed package.

**Solution:**
1. Create/update `MANIFEST.in` with all necessary file types (see above)
2. Ensure `recursive-include your_app_name *.js` is present
3. Reinstall the app: `pip install -e .` in development or `bench get-app` from scratch
4. Verify installation: Check that `site-packages/your_app/public/js/` contains your files

**Related Issues:**
- [frappe/frappe#26346](https://github.com/frappe/frappe/issues/26346)
- [frappe/frappe#28410](https://github.com/frappe/frappe/issues/28410)

### Build Errors with esbuild (Other Causes)
- **No build.json:** Remove `build.json` entirely (not even empty `{}`). Reference apps like `red_background` don't have this file at all.
- **Root hooks.py conflict:** With `pyproject.toml`, only keep `hooks.py` in the module directory, not in the root
- **JavaScript will still load:** Via `hooks.py` configuration, no build process needed for simple apps

### Version Not Found
- **Solution:** Ensure `__version__` is defined in `__init__.py`
- Check that `pyproject.toml` has `dynamic = ["version"]`
- Both `__init__.py` and `__version__.py` should have the same version string

### Module Import Errors
- **Solution:** Verify package name matches directory name
- Check that `__init__.py` exists in the module directory
- Ensure the app is pip-installed in the bench's virtual environment
- Activate virtualenv before installing: `source env/bin/activate && pip install -e .`

### Assets Not Loading
- **Solution:** Check paths in `hooks.py` match actual file locations
- Verify files exist in `public/js/` directory
- **Most importantly:** Check `MANIFEST.in` includes the necessary file types
- Clear browser cache and run `bench clear-cache`
- Reinstall app if `MANIFEST.in` was updated after initial installation
