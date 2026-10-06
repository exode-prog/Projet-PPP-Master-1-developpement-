#include <tunables/global>

profile mcp-vulnerable-hardened flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/python>
  #include <abstractions/nameservice>
  #include <abstractions/ssl_certs>

  network inet tcp,
  network inet udp,
  network inet raw,

  # Interpreteur Python + bibliotheques (chemins reels de l'image python:3.12-slim)
  /usr/local/bin/python3*     mrix,
  /usr/local/lib/python3*/**  mr,
  /usr/local/lib/*.so*        mr,
  /usr/local/lib/**           mr,
  /usr/bin/python3*           mr,
  /usr/lib/python3*/**        mr,
  /usr/lib/**.so*             mr,

  # Application
  /app/            r,
  /app/**          r,

  # Outils necessaires a ping_host (shell + ping, via subprocess shell=True)
  /bin/dash        mrix,
  /usr/bin/dash    mrix,
  /bin/sh          mrix,
  /bin/ping        mrix,
  /usr/bin/ping    mrix,

  /tmp/**          rw,

  # Deny explicite : empeche toute tentative de lecture/ecriture hors du
  # perimetre attendu, meme si une faille applicative tente d'y acceder
  deny /etc/shadow        rwklx,
  deny /etc/passwd        w,
  deny /root/**           rwklx,
  deny /home/**           rwklx,
  deny /boot/**           rwklx,
  deny /sys/firmware/**   rwklx,
  deny /sys/kernel/**     rwklx,
  deny @{PROC}/sys/kernel/** rwklx,
  deny @{PROC}/sysrq-trigger rwklx,
  deny @{PROC}/kcore       rwklx,
  deny @{PROC}/*/mem       rwklx,
  deny /var/run/docker.sock rwklx,

  deny ptrace,
  deny capability,
}
