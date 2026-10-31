from contextlib import contextmanager

import routeros_api
from django.conf import settings
from routeros_api.exceptions import RouterOsApiConnectionError, RouterOsApiError

from customers.models import InternetPackage
from network.credentials import NetworkCredentialError, decrypt_secret
from network.models import NetworkNode, ProvisioningRequest
from network.providers.stub import (
    BaseProvisioningProvider,
    ProvisioningProviderError,
    ProvisioningProviderResult,
)


PPP_SECRET_PATH = "/ppp/secret"
PPP_ACTIVE_PATH = "/ppp/active"


def _router_host(node: NetworkNode) -> str:
    return (node.router_api_host or node.management_ip or "").strip()


@contextmanager
def router_api_session(node: NetworkNode):
    """Open an authenticated RouterOS API session for a node and always close it."""
    host = _router_host(node)
    if not host:
        raise ProvisioningProviderError(
            f"Node {node.code} has no router API host or management IP configured."
        )
    if not node.router_api_username:
        raise ProvisioningProviderError(
            f"Node {node.code} has no router API username configured."
        )

    try:
        password = decrypt_secret(node.router_api_password_encrypted)
    except NetworkCredentialError as exc:
        raise ProvisioningProviderError(str(exc)) from exc

    pool = routeros_api.RouterOsApiPool(
        host,
        username=node.router_api_username,
        password=password,
        port=node.router_api_port or None,
        # RouterOS 6.43+ and 7.x only accept plaintext login over the API.
        plaintext_login=True,
        use_ssl=node.router_api_use_tls,
        # Most ISP routers use self-signed API certificates.
        ssl_verify=False,
        ssl_verify_hostname=False,
    )
    pool.socket_timeout = settings.MIKROTIK_API_TIMEOUT_SECONDS

    try:
        api = pool.get_api()
    except (RouterOsApiConnectionError, OSError) as exc:
        # The library wraps socket timeouts and refusals in its connection error.
        raise ProvisioningProviderError(
            f"Could not reach router {node.code} ({host}): {exc}"
        ) from exc
    except RouterOsApiError as exc:
        raise ProvisioningProviderError(
            f"Could not log in to router {node.code} ({host}): {exc}"
        ) from exc

    try:
        yield api
    except RouterOsApiConnectionError as exc:
        raise ProvisioningProviderError(
            f"Connection to router {node.code} was interrupted: {exc}"
        ) from exc
    except RouterOsApiError as exc:
        raise ProvisioningProviderError(
            f"Router {node.code} rejected the command: {exc}"
        ) from exc
    except OSError as exc:
        raise ProvisioningProviderError(
            f"Connection to router {node.code} was interrupted: {exc}"
        ) from exc
    finally:
        pool.disconnect()


def read_router_identity(node: NetworkNode) -> dict:
    with router_api_session(node) as api:
        identity = api.get_resource("/system/identity").get()
        resource = api.get_resource("/system/resource").get()

    identity_row = identity[0] if identity else {}
    resource_row = resource[0] if resource else {}
    return {
        "identity": identity_row.get("name", ""),
        "version": resource_row.get("version", ""),
        "board_name": resource_row.get("board-name", ""),
        "uptime": resource_row.get("uptime", ""),
    }


def _package_profile(package: InternetPackage) -> str:
    return (package.router_profile or package.code).strip()


class MikroTikProvisioningProvider(
    BaseProvisioningProvider
):
    """
    Provisions PPPoE subscribers on MikroTik RouterOS through the API service
    (port 8728, or 8729 with TLS). Every action converges the router onto the
    desired secret state, so retries after a partial failure are safe.
    """

    def execute(
        self,
        *,
        provisioning_request: ProvisioningRequest,
    ) -> ProvisioningProviderResult:
        assignment = provisioning_request.network_assignment
        if assignment is None:
            raise ProvisioningProviderError(
                "Provisioning request has no network assignment."
            )

        node = assignment.network_node
        service_account = provisioning_request.service_account
        username = assignment.username.strip()
        if not username:
            raise ProvisioningProviderError(
                f"Service {service_account.service_number} has no PPPoE username."
            )

        try:
            password = decrypt_secret(assignment.network_password_encrypted)
        except NetworkCredentialError as exc:
            raise ProvisioningProviderError(str(exc)) from exc

        action = provisioning_request.action
        package = service_account.internet_package
        if action == ProvisioningRequest.Action.CHANGE_PACKAGE:
            package = self._resolve_target_package(provisioning_request)

        with router_api_session(node) as api:
            ppp_secrets = api.get_resource(PPP_SECRET_PATH)
            existing = ppp_secrets.get(name=username)
            secret = existing[0] if existing else None

            if action == ProvisioningRequest.Action.SUSPEND:
                # A subscriber without a secret already cannot connect.
                if secret is not None:
                    ppp_secrets.set(id=secret["id"], disabled="yes")
                self._drop_active_sessions(api, username)
                outcome = "DISABLED" if secret is not None else "SECRET_ABSENT"

            elif action in {
                ProvisioningRequest.Action.ACTIVATE,
                ProvisioningRequest.Action.RESTORE,
                ProvisioningRequest.Action.CHANGE_PACKAGE,
            }:
                desired = {
                    "profile": _package_profile(package),
                    "comment": service_account.service_number,
                    "disabled": "no",
                }
                if password:
                    desired["password"] = password

                if secret is None:
                    if not password:
                        raise ProvisioningProviderError(
                            f"Service {service_account.service_number} has no stored "
                            "PPPoE password, so its secret cannot be created on the router."
                        )
                    ppp_secrets.add(name=username, service="pppoe", **desired)
                    outcome = "CREATED"
                else:
                    ppp_secrets.set(id=secret["id"], **desired)
                    outcome = "UPDATED"

                if action == ProvisioningRequest.Action.CHANGE_PACKAGE:
                    # Reconnect so the new rate-limit profile applies immediately.
                    self._drop_active_sessions(api, username)

            else:
                raise ProvisioningProviderError(
                    "Provisioning action is not supported "
                    "by the MikroTik provider."
                )

        return ProvisioningProviderResult(
            provider_reference=(
                f"MIKROTIK-{node.code}-{action}-{username}"
            ),
            metadata={
                "provider": "MIKROTIK",
                "action": action,
                "node_code": node.code,
                "username": username,
                "profile": _package_profile(package),
                "outcome": outcome,
            },
        )

    @staticmethod
    def _drop_active_sessions(api, username: str) -> None:
        active = api.get_resource(PPP_ACTIVE_PATH)
        for session in active.get(name=username):
            active.remove(id=session["id"])

    @staticmethod
    def _resolve_target_package(
        provisioning_request: ProvisioningRequest,
    ) -> InternetPackage:
        target_package_id = (
            provisioning_request.requested_payload.get("target_package_id")
        )
        try:
            return (
                InternetPackage.objects
                .for_organization(provisioning_request.organization)
                .get(id=target_package_id)
            )
        except (InternetPackage.DoesNotExist, ValueError) as exc:
            raise ProvisioningProviderError(
                "Target package for this change was not found."
            ) from exc
