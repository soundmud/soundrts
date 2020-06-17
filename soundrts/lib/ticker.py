from threading import Event as _Event, Thread as _Thread


class Ticker(_Thread):
    """Call a function every number of seconds:

    t = Ticker(30.0, f, args=[], kwargs={})
    t.start()
    t.cancel() # stop the ticker's action
    """

    daemon = True

    def __init__(self, interval, function, args=[], kwargs={}):
        _Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = _Event()

    def cancel(self):
        """Stop the ticker"""
        self.finished.set()

    def run(self):
        while not self.finished.isSet():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


if __name__ == "__main__":
    import time
    def _print_tick():
        print("tick")
    t = Ticker(1.0, _print_tick)
    print("start...")
    t.start()
    time.sleep(5)
    print("cancel...")
    t.cancel()
    time.sleep(5)
