"""
Start plugin services.

This module also applies small portal-side compatibility patches that
must load with the Portal process itself.
"""

from evennia.server.portal import portalsessionhandler


def _patch_portal_server_disconnect():
    original = portalsessionhandler.PortalSessionHandler.server_disconnect
    if getattr(original, "_dragonsire_accepts_sessid", False):
        return

    def patched(self, session, reason=""):
        if session and not hasattr(session, "disconnect"):
            try:
                session = self.get(int(session))
            except (TypeError, ValueError):
                session = None
        return original(self, session, reason=reason)

    patched._dragonsire_accepts_sessid = True
    portalsessionhandler.PortalSessionHandler.server_disconnect = patched


def start_plugin_services(portal):
    """
    This hook is called by Evennia, last in the Portal startup process.

    portal - a reference to the main portal application.
    """
    _patch_portal_server_disconnect()
