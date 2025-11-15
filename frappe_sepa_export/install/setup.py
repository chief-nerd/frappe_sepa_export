import frappe


def before_install():
    """Setup requirements for SEPA export functionality"""
    pass


def after_install():
    """Setup after app installation"""
    import_needed_dependencies()


def import_needed_dependencies():
    """Import any needed dependencies for the app to function properly"""
    # Add BeautifulSoup to requirements
    try:
        import bs4
    except ImportError:
        import subprocess
        import sys
        
        frappe.log_error("Installing BeautifulSoup for SEPA Export")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
        
    # Add a system notification about using standard Bank Account doctype
    frappe.publish_realtime(
        event="msgprint",
        message="SEPA File Export installed. Please ensure suppliers have Bank Account records configured.",
        user=frappe.session.user
    )
