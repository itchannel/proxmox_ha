class ProxmoxClient:
    """A wrapper for the proxmoxer ProxmoxAPI client."""

    def __init__(self, host, port, user, realm, password, verify_ssl):
        """Initialize the ProxmoxClient."""

        self._host = host
        self._port = port
        self._user = user
        self._realm = realm
        self._password = password
        self._verify_ssl = verify_ssl

        self._proxmox = None
        self._connection_start_time = None

    def build_client(self):
        """Construct the ProxmoxAPI client. Allows inserting the realm within the `user` value."""

        if "@" in self._user:
            user_id = self._user
        else:
            user_id = f"{self._user}@{self._realm}"

        self._proxmox = ProxmoxAPI(
            self._host,
            port=self._port,
            user=user_id,
            password=self._password,
            verify_ssl=self._verify_ssl,
        )

    def get_api_client(self):
        """Return the ProxmoxAPI client."""
        return self._proxmox
