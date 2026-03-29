from django.conf import settings

from evennia.server.portal import telnet as evennia_telnet
from evennia.utils.utils import delay


class NoMCCPTelnetProtocol(evennia_telnet.TelnetProtocol):
    def connectionMade(self):
        self.do(evennia_telnet.LINEMODE).addErrback(self._wont_linemode)
        self.line_buffer = b""
        client_address = self.transport.client
        client_address = client_address[0] if client_address else None
        self.handshakes = 7
        self.init_session(self.protocol_key, client_address, self.factory.sessionhandler)
        self.protocol_flags["ENCODING"] = settings.ENCODINGS[0] if settings.ENCODINGS else "utf-8"
        self.sessionhandler.connect(self)

        self.sga = evennia_telnet.suppress_ga.SuppressGA(self)
        self.naws = evennia_telnet.naws.Naws(self)
        self.ttype = evennia_telnet.ttype.Ttype(self)
        self.protocol_flags["MCCP"] = False
        self.mssp = evennia_telnet.mssp.Mssp(self)
        self.oob = evennia_telnet.telnet_oob.TelnetOOB(self)
        self.mxp = evennia_telnet.Mxp(self)

        self._handshake_delay = delay(2, callback=self.handshake_done, timeout=True)
        self.transport.setTcpKeepAlive(1)
        self.protocol_flags["NOPKEEPALIVE"] = True
        self.nop_keep_alive = None
        self.toggle_nop_keepalive()

    def enableRemote(self, option):
        if option == evennia_telnet.MCCP:
            return False
        return super().enableRemote(option)

    def disableRemote(self, option):
        if option == evennia_telnet.MCCP:
            return False
        return super().disableRemote(option)


TelnetProtocol = NoMCCPTelnetProtocol