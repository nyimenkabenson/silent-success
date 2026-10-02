"""The three TCP targets this demo probes, then idle.

  9001  accepts and replies            -> probe records "allowed"
  9002  nothing listening              -> probe records "refused"
  9003  accepts and never replies      -> probe records "timeout"

Port 9003 is the case that makes the mismatch scenario real: the connection
succeeds, so this is not a refusal, but nothing answers, so it is not an
allow either. A checker that reduces "any nonzero exit" to deny turns that
into a safety verdict the probe never supported.
"""
import socket
import threading

HELD = []  # keep silent connections open; closing them would look like a reply


def serve(port, reply):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(16)
    while True:
        conn, _ = s.accept()
        if reply:
            try:
                conn.recv(64)
                conn.sendall(b"PONG\n")
            except OSError:
                pass
            conn.close()
        else:
            HELD.append(conn)


for port, reply in ((9001, True), (9003, False)):
    threading.Thread(target=serve, args=(port, reply), daemon=True).start()

print("targets up: 9001 replies, 9002 closed, 9003 silent", flush=True)
threading.Event().wait()
