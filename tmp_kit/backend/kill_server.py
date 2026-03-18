import psutil
import os
import signal

def detailed_process_info(proc):
    try:
        return f"PID: {proc.pid}, Name: {proc.name()}, Cmdline: {proc.cmdline()}"
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "Process unavailable"

def kill_process_on_port(port):
    killed = False
    print(f"Scanning for process on port {port}...")
    for proc in psutil.process_iter():
        try:
            # Check connections
            try:
                conns = proc.net_connections()
            except (psutil.AccessDenied, psutil.ZombieProcess):
                continue

            for conn in conns:
                if conn.laddr.port == port:
                    print(f"Found process on port {port}: PID={proc.pid}, Name={proc.name()}")
                    try:
                        proc.kill()
                        killed = True
                        print(f"Process {proc.pid} killed.")
                    except Exception as e:
                        print(f"Failed to kill process {proc.pid}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    if not killed:
        print(f"No process found listening on port {port}.")

if __name__ == "__main__":
    kill_process_on_port(8000)
