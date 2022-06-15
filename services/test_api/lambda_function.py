from layers.base import EventBase, ResultBase, Response

def handler(e, c):
    event = Event(e, c)
    event.handle()
    return event.response()

class Result(ResultBase):
    HELLO_WOLRD = (200, "HELLO_WOLRD", "HELLO_WOLRD")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)

    def handle(self):
        self._response = Response(Result.HELLO_WOLRD, {'hello': 'world'}).to_json()