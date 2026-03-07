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

**CRITICAL: Every directory in the module path must contain an `__init__.py` file.** This includes:
- `sepa_file_export/` (the module directory)
- `sepa_file_export/doctype/` (the doctype container)
- `sepa_file_export/doctype/sepa_settings/` (each individual doctype)

Missing any `__init__.py` will cause "Module not found" errors at runtime even though the files exist on disk.

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
- Check that `__init__.py` exists in **every** directory in the module path (including `doctype/`)
- Ensure the app is pip-installed in the bench's virtual environment
- Activate virtualenv before installing: `source env/bin/activate && pip install -e .`
- See the **Frappe Module System** section below for detailed diagnostics

### "Module X not found" in the Browser
**Root Cause:** One of two things (or both):
1. The `Module Def` record doesn't exist in the database
2. A `__init__.py` file is missing in the module's directory hierarchy

**Solution:** See the **Diagnosing "Module Not Found" Errors** section below for a step-by-step checklist.

### Assets Not Loading
- **Solution:** Check paths in `hooks.py` match actual file locations
- Verify files exist in `public/js/` directory
- **Most importantly:** Check `MANIFEST.in` includes the necessary file types
- Clear browser cache and run `bench clear-cache`
- Reinstall app if `MANIFEST.in` was updated after initial installation

## ListView Customisation in Frappe v15

### Loading List View JavaScript

Register a list-view JS file in `hooks.py`:

```python
doctype_list_js = {"Purchase Invoice": "public/js/purchase_invoice_list.js"}
```

### Chaining `onload` with Other Apps

ERPNext (or other apps) may already define `frappe.listview_settings['Purchase Invoice']` with its own `onload`. If you overwrite it with `Object.assign`, the original is lost. Always save and chain the existing handler:

```javascript
{
    const existing_settings = frappe.listview_settings['Purchase Invoice'] || {};
    const existing_onload = existing_settings.onload;

    frappe.listview_settings['Purchase Invoice'] = Object.assign(
        existing_settings,
        {
            onload(listview) {
                if (existing_onload) existing_onload.call(this, listview);
                // … your custom code here …
            }
        }
    );
}
```

The wrapping `{ }` block scope keeps the `existing_onload` reference private.

### Adding Items to the List-View "Actions" Dropdown (v15)

When the user checks items in a list view, Frappe v15 shows an **"Actions"** dropdown in the toolbar. This dropdown is **not** a regular page button group — it is built dynamically every time from `ListView.get_actions_menu_items()`.

**What does NOT work:**

| Approach | Why it fails |
|---|---|
| `listview.page.add_action_item(label, fn)` | Adds to the page's kebab/three-dot **Menu**, not the selection "Actions" dropdown. The Menu is hidden when items are checked. |
| `listview.page.add_inner_button(label, fn, __('Actions'))` | Creates a *new* "Actions" button group in the page header. This is a separate element from the built-in selection "Actions" dropdown. |

**What works — monkey-patch `get_actions_menu_items()`:**

```javascript
onload(listview) {
    const _orig = listview.get_actions_menu_items.bind(listview);
    listview.get_actions_menu_items = function () {
        const items = _orig();
        items.push({
            label: __('Export SEPA XML'),
            action: () => {
                const selected = listview.get_checked_items();
                if (!selected.length) return;
                do_something(selected);
            },
            standard: true
        });
        return items;
    };
}
```

Each item in the array is an object with:
- `label` — display text
- `action` — callback function
- `standard` — set `true` to always show (not gated by permissions)

### Data Available from `listview.get_checked_items()`

`get_checked_items()` returns only the **fields rendered in the list view columns**. If a field like `company` or `bill_no` is not displayed in the list, it will be `undefined`. Do **not** rely on arbitrary fields being present.

**Workaround:** Collect only the `name` values from the selection, then fetch full details via a dedicated backend endpoint:

```javascript
const names = selected.map(d => d.name);
frappe.call({
    method: 'your_app.utils.get_full_details',
    args: { names: JSON.stringify(names) }
});
```

## Frappe Module System: How It Works

### Module Def Records

Frappe resolves modules via `Module Def` records in the database. Each module (listed in `modules.txt`) must have a corresponding `Module Def` record with:
- `module_name` — the human-readable name (e.g., "SEPA File Export")
- `app_name` — the Python package name (e.g., "frappe_sepa_export")

These records are normally created during `bench install-app`. If the record is missing (e.g., due to a failed install or manual DB manipulation), any DocType belonging to that module will show:

```
Module SEPA File Export not found
The resource you are looking for is not available
```

### Module Directory ↔ modules.txt Mapping

Frappe converts the module name in `modules.txt` to a directory name by:
1. Lowering the case
2. Replacing spaces with underscores

So `SEPA File Export` → `sepa_file_export/`

### The `__init__.py` Requirement

**Every directory in the Python package path must contain an `__init__.py` file** (even if empty). This is a standard Python packaging requirement, but it's easy to miss in Frappe apps because there are many nested directories.

For the SEPA Settings DocType, the full import path is:
```
frappe_sepa_export.sepa_file_export.doctype.sepa_settings.sepa_settings
```

This means **all** of these directories need `__init__.py`:
```
frappe_sepa_export/
frappe_sepa_export/__init__.py                              ✅
frappe_sepa_export/sepa_file_export/
frappe_sepa_export/sepa_file_export/__init__.py              ✅
frappe_sepa_export/sepa_file_export/doctype/
frappe_sepa_export/sepa_file_export/doctype/__init__.py      ✅ ← commonly missed!
frappe_sepa_export/sepa_file_export/doctype/sepa_settings/
frappe_sepa_export/sepa_file_export/doctype/sepa_settings/__init__.py  ✅
```

If any `__init__.py` is missing, Python cannot traverse the package path. Frappe will report "Module not found" even though the Module Def record exists in the database and the files are on disk.

### Ensuring Module Def Exists Programmatically

The `after_install` hook can create the Module Def record as a safety net:

```python
# install/setup.py
import frappe

def after_install():
    create_module_def()

def create_module_def():
    if not frappe.db.exists("Module Def", "SEPA File Export"):
        module_def = frappe.new_doc("Module Def")
        module_def.module_name = "SEPA File Export"
        module_def.app_name = "frappe_sepa_export"
        module_def.insert(ignore_permissions=True)
        frappe.db.commit()
```

### Diagnosing "Module Not Found" Errors

When you see "Module X not found", check in this order:

1. **Module Def record exists?** — `bench console` → `frappe.db.exists("Module Def", "SEPA File Export")`
2. **All `__init__.py` files present?** — `find apps/frappe_sepa_export -type d | while read d; do [ -f "$d/__init__.py" ] || echo "MISSING: $d/__init__.py"; done`
3. **DocType JSON has correct module?** — Check `"module": "SEPA File Export"` in the DocType JSON matches `modules.txt` exactly
4. **App is pip-installed?** — `pip show frappe-sepa-export` should show the package
5. **Bench migrate ran?** — DocTypes are synced from JSON to DB during `bench migrate`

## Docker / Containerized Deployment

### How the App Gets Into the Container

There are several ways a Frappe app can end up in a Docker container:

| Method | Has `.git`? | `bench get-app` works? | Update method |
|---|---|---|---|
| `bench get-app` inside container | ✅ Yes | ✅ Yes | `cd apps/app && git pull && cd ../.. && bench migrate` |
| Baked into Docker image via pip | ❌ No | ❌ No (directory exists but no git) | Rebuild Docker image |
| Volume-mounted from host | Depends | Depends | Edit on host, restart container |
| Copied via Dockerfile `COPY` | ❌ No | ❌ No | Rebuild Docker image |

### Common Docker Pitfalls

#### "fatal: not a git repository"
**Cause:** The app was installed via pip (in Dockerfile or during image build), not via `bench get-app`. There's no `.git` directory.

**Solution:** Either:
- Reinstall properly: `bench get-app <url>` (clones via git)
- Or rebuild the Docker image with the updated code

#### "No app named X" when trying `bench remove-app`
**Cause:** The app isn't registered in bench's app registry. It may have been pip-installed directly or added to the Docker image outside of bench's workflow.

**Solution:** Install fresh via bench:
```bash
cd ~/frappe-bench
bench get-app frappe_sepa_export https://github.com/chief-nerd/frappe_sepa_export
bench --site <site-name> install-app frappe_sepa_export
```

#### FileNotFoundError after `bench get-app` overwrites directory
**Cause:** Running `bench get-app` while your shell's cwd is inside `apps/frappe_sepa_export/`. The directory gets archived and replaced, so the shell's cwd no longer exists.

**Solution:** Always run bench commands from `~/frappe-bench`:
```bash
cd ~/frappe-bench
bench get-app frappe_sepa_export https://github.com/chief-nerd/frappe_sepa_export
```

#### Local edits not reflected in container
**Cause:** Editing files on the host machine doesn't automatically sync to the container unless the directory is volume-mounted.

**Solution:** Either:
- Volume-mount the app directory in `docker-compose.yml`
- Or push to git, then `git pull` inside the container (requires git-based install)
- Or rebuild the Docker image

### Update Workflow for Docker Deployments

For a git-based install inside the container:
```bash
cd ~/frappe-bench
cd apps/frappe_sepa_export && git pull && cd ../..
bench build --app frappe_sepa_export
bench --site <site-name> migrate
bench restart
```

For a pip-based install (no git): rebuild the Docker image with the updated code and redeploy.

### Quick Fix: Creating Files Inside the Container

When you need an immediate fix (like a missing `__init__.py`) without rebuilding:
```bash
# Inside the container
touch ~/frappe-bench/apps/frappe_sepa_export/path/to/__init__.py
bench --site <site-name> migrate
bench restart
```

This is a temporary fix — the change will be lost if the container is recreated. Always commit the fix to git for persistence.
