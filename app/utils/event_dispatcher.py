class EventDispatcher:
    NEW_ROOMMATE_CREATED = "new_roommate_created"
    NEW_STICKER_CREATED = "new_sticker_created"
    NEW_CAST_CREATED = "new_cast_created"

    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_type: str, listener):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
        print(f"{listener} subscribes {event_type}")

    def dispatch(self, event_type: str, *args, **kwargs):
        print("event type : ", event_type)
        print(self._listeners)
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                listener(*args, **kwargs)

dispatcher = EventDispatcher()