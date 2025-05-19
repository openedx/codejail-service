3. Unauthenticated API
######################

Status
******

**Accepted** *2025-01-13*

Context
*******

While codejail-service does not store or process particularly sensitive data, it does provide computation resources. This indicates that authentication or other API call limitations may be warranted.

For its intended purpose (implementing remote codejail, for LMS and CMS), the service is not required to be directly exposed to the public internet. Codejail execution in edxapp is only available to logged-in users, although those users may not need to have verified accounts (depending on deployment settings).

There is currently no provision in the API client code for passing authentication.

Decision
********

codejail-service will not require authentication for its API calls, but will instead document that the service should not be exposed to the public internet.

Consequences
************

Deployments that inadvertently expose the service risk abuse of the compute resources. Any vulnerabilities in the webapp's communication with codejail (as opposed to inside the sandbox itself) may also be exposed in such a situation.

Deferred Alternatives
*********************

While codejail-service doesn't have a database (by design, see ADR 2) it could still authenticate the caller as another service in the deployment. For example, asymmetric JWT tokens could be used to authenticate the caller as edxapp. (Symmetric auth would be unsuitable, as a partial confinement failure could then expose the locally stored keys to an attacker.)

It may still be worth adding the option of authentication at some point, but the risk is relatively low (as the service is already designed to be locked down) and exploitation would require the existence of an API vulnerability and an attacker who can reach the service directly (via SSRF, a misconfigured deployment, or pivoting from the internal network after an unrelated compromise).

This would require modifications to ``remote_exec.py`` in edxapp and additional configuration work in both services.
