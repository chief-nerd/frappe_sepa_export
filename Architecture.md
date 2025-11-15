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
├── MANIFEST.in                 # Specifies which files to include in package
├── requirements.txt            # Python dependencies
├── package.json                # Node.js metadata (minimal for Frappe apps)
├── README.md                   # Documentation
├── hooks.py                    # (Optional) Root hooks for compatibility
└── frappe_sepa_export/         # Main app module
    ├── __init__.py             # Module initialization with __version__
    ├── __version__.py          # Version definition
    ├── hooks.py                # Frappe hooks configuration (PRIMARY)
    ├── public/                 # Static assets
    │   ├── build.json          # Empty {} for no bundling
    │   └── js/                 # JavaScript files
    │       ├── frappe_sepa_export.js
    │       └── purchase_invoice.js
    ├── config/                 # App configuration
    │   └── frappe_sepa_export.py
    ├── doctype/                # Custom DocTypes
    ├── install/                # Installation scripts
    └── utils.py                # Utility functions
```

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

With an empty `build.json`:
```json
{}
```

**Benefits:**
- No build process needed
- Files served directly
- Faster development
- Simpler debugging

### 2. Bundled Loading (For Complex Apps)
If using ES6 imports, TypeScript, or complex bundling:

```json
{
    "js/frappe_sepa_export.js": [
        "public/js/module1.js",
        "public/js/module2.js"
    ]
}
```

This requires esbuild to process the files during `bench build`.

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

1. **Keep JavaScript simple** - Avoid complex bundling unless necessary
2. **Use semantic versioning** - Follow MAJOR.MINOR.PATCH format
3. **Minimize dependencies** - Only include what's truly needed
4. **Empty build.json** - Unless you need asset bundling
5. **Module hooks** - Place hooks.py in the module directory for pyproject.toml apps
6. **Type hints** - Use Python type annotations for better IDE support
7. **Documentation** - Keep README.md updated with installation and usage instructions

## References

Successful Frappe apps following this structure:
- [red_background](https://github.com/alyf-de/red_background) - Minimal app example
- [erpnext_pdf-on-submit](https://github.com/alyf-de/erpnext_pdf-on-submit) - Feature-rich app
- [frappe/hrms](https://github.com/frappe/hrms) - Large-scale official app

## Troubleshooting

### Build Errors with esbuild
- **Solution:** Use empty `build.json` (`{}`) if you don't need bundling
- JavaScript will still load via `hooks.py` configuration

### Version Not Found
- **Solution:** Ensure `__version__` is defined in `__init__.py`
- Check that `pyproject.toml` has `dynamic = ["version"]`

### Module Import Errors
- **Solution:** Verify package name matches directory name
- Check that `__init__.py` exists in the module directory

### Assets Not Loading
- **Solution:** Check paths in `hooks.py` match actual file locations
- Verify files exist in `public/js/` directory
- Clear browser cache and run `bench clear-cache`
