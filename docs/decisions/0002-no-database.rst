.. _adr2-no-db:

2. No database
##############

Status
******

**Accepted** *2025-01-13*

Context
*******

An early decision we had to make in the design of a remote codejail service was whether to include a database. A database would provide several possible benefits, such as enabling an admin dashboard for configuration (e.g. Waffle flags) or audit logging of submitted code. Django and its ecosystem also expect there to be a database.

 On the other hand, supporting a database would complicate isolation. The value of configuration flags would also be of limited use, as they could not include anything related to security; a partial confinement failure could lead to malicious code changing the application's settings, escalating its own privileges.

Decision
********

codejail-service will not have any database connection.

Consequences
************

Django will be configured to use an in-memory SQLite DB. There will be no persistence mechanism.

It will be possible to lock down outbound networking entirely on the service, and the service will not be required to hold any connection-related secrets.

Any audit logging will be performed on the edxapp site. That would be a better option for logging anyhow, as edxapp has more context on the submitted student code, and what codejail-service receives has already been wrapped in a standard template along with compatibility shims and other support code (more than we want to include in the audit log).
