import os
import sys
import argparse
import logging
from importlib import metadata

# ✅ Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ Optional: File-based logging
try:
    root_logger = logging.getLogger()
    log_file_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(log_file_dir, 'mcp_server_debug.log')

    file_handler = logging.FileHandler(log_file_path, mode='a')
    file_handler.setLevel(logging.DEBUG)

    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(threadName)s '
        '[%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    logger.debug(f"Detailed file logging configured to: {log_file_path}")
except Exception as e:
    sys.stderr.write(f"CRITICAL: Failed to set up file logging: {e}\n")

# ✅ App imports AFTER logging
from core.server import server, set_transport_mode
from core.utils import check_credentials_directory_permissions

def safe_print(text):
    if not sys.stderr.isatty():
        logger.debug(f"[MCP Server] {text}")
        return
    try:
        print(text, file=sys.stderr)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode(), file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description='Google Workspace MCP Server')
    parser.add_argument('--single-user', action='store_true')
    parser.add_argument('--tools', nargs='*', choices=[
        'gmail', 'drive', 'calendar', 'docs', 'sheets',
        'chat', 'forms', 'slides', 'tasks', 'search'
    ])
    parser.add_argument('--transport', choices=['stdio', 'streamable-http'], default='stdio')
    parser.add_argument('--port', type=int, default=8000, help='Port the server should listen on')  # ✅ added
    args = parser.parse_args()

    port = args.port  # ✅ use parsed port
    base_uri = os.getenv("WORKSPACE_MCP_BASE_URI", "http://localhost")

    safe_print("🔧 Google Workspace MCP Server")
    try:
        version = metadata.version("workspace-mcp")
    except metadata.PackageNotFoundError:
        version = "dev"

    safe_print(f"📦 Version: {version}")
    safe_print(f"🌐 Transport: {args.transport}")
    if args.transport == 'streamable-http':
        safe_print(f"🔗 URL: {base_uri}:{port}")
        safe_print(f"🔐 OAuth Callback: {base_uri}:{port}/oauth2callback")
    safe_print(f"👤 Mode: {'Single-user' if args.single_user else 'Multi-user'}")
    safe_print(f"🐍 Python: {sys.version.split()[0]}")
    safe_print("")

    tool_imports = {
        'gmail': lambda: __import__('gmail.gmail_tools'),
        'drive': lambda: __import__('gdrive.drive_tools'),
        'calendar': lambda: __import__('gcalendar.calendar_tools'),
        'docs': lambda: __import__('gdocs.docs_tools'),
        'sheets': lambda: __import__('gsheets.sheets_tools'),
        'chat': lambda: __import__('gchat.chat_tools'),
        'forms': lambda: __import__('gforms.forms_tools'),
        'slides': lambda: __import__('gslides.slides_tools'),
        'tasks': lambda: __import__('gtasks.tasks_tools'),
        'search': lambda: __import__('gsearch.search_tools')
    }

    tool_icons = {
        'gmail': '📧', 'drive': '📁', 'calendar': '📅',
        'docs': '📄', 'sheets': '📊', 'chat': '💬',
        'forms': '📝', 'slides': '🖼️', 'tasks': '✓', 'search': '🔍'
    }

    tools_to_import = args.tools if args.tools else tool_imports.keys()
    safe_print(f"🛠️  Loading {len(tools_to_import)} tool modules:")
    for tool in tools_to_import:
        tool_imports[tool]()
        safe_print(f"   {tool_icons[tool]} {tool.title()}")

    if args.single_user:
        os.environ['MCP_SINGLE_USER_MODE'] = '1'
        safe_print("🔐 Single-user mode enabled")

    try:
        safe_print("🔍 Checking credentials directory permissions...")
        check_credentials_directory_permissions()
        safe_print("✅ Credentials directory ready")
    except Exception as e:
        logger.error(f"Credential check failed: {e}")
        sys.exit(1)

    try:
        set_transport_mode(args.transport)
        if args.transport == 'streamable-http':
            safe_print(f"🚀 Starting server on {base_uri}:{port}")
            server.run(transport="streamable-http")
        else:
            safe_print("🚀 Starting in stdio mode")
            from auth.oauth_callback_server import ensure_oauth_callback_available
            success, error = ensure_oauth_callback_available('stdio', port, base_uri)
            if success:
                safe_print(f"🔐 OAuth callback server started on {base_uri}:{port}/oauth2callback")
            server.run()
    except Exception as e:
        logger.error(f"Unexpected server error: {e}", exc_info=True)
        from auth.oauth_callback_server import cleanup_oauth_callback_server
        cleanup_oauth_callback_server()
        sys.exit(1)

if __name__ == "__main__":
    main()
