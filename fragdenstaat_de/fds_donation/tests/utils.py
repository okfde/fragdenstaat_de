import select
import signal
import subprocess
import threading
from queue import Queue


def subprocess_reader(process_args, stop_event, queue):
    proc = subprocess.Popen(
        process_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    poll_obj = select.poll()
    poll_obj.register(proc.stdout, select.POLLIN)
    while True:
        if stop_event.is_set():
            break
        poll_result = poll_obj.poll(1)
        if poll_result:
            line = proc.stdout.readline()
            if line:
                queue.put(line)
        returncode = proc.poll()
        if returncode is not None:
            break
    poll_obj.unregister(proc.stdout)
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(2)
    except subprocess.TimeoutExpired:
        proc.kill()


class ProcessReader:
    def __init__(self, process_args):
        self.process_args = process_args
        self.thread = None
        self.queue = Queue[str]()
        self.stop_event = threading.Event()

    def start(self):
        if self.thread:
            raise Exception("Process already started")
        self.thread = threading.Thread(
            target=subprocess_reader,
            args=(self.process_args, self.stop_event, self.queue),
        )
        self.thread.start()
        return self

    def readline(self):
        if not self.thread:
            raise Exception("Process not started")
        return self.queue.get()

    def stop(self):
        if not self.thread:
            raise Exception("Process not started")
        self.stop_event.set()
        self.thread.join()
