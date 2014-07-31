import threading
import time

import pygame
from pygame.locals import KEYDOWN

from clientmediasound import DEFAULT_VOLUME, VoiceChannel


class Message(object):

    def __init__(self, lns, lv=DEFAULT_VOLUME, rv=DEFAULT_VOLUME, said=False, expiration_delay=45, update_type=None):
        self.lns = lns
        self.lv = lv
        self.rv = rv
        self.said = said
        self.expiration_time = time.time() + expiration_delay
        self.update_type = update_type

    def unpack(self):
        return (self.lns, self.lv, self.rv)

    def has_expired(self):
        return self.expiration_time < time.time()


class _Voice(object):
    
    msgs = [] # said and unsaid messages
    active = False # currently talking (not just self.item())
    history = False # in "history" mode
    current = 0 # index of the message currently said
                # == len(self.msgs) if no message

    def get_unsaid(self): # index of the first never said message (== len(self.msgs) if no unsaid message)
        for i, m in enumerate(self.msgs):
            if not m.said:
                return i
        return len(self.msgs)

    unsaid = property(get_unsaid)

    def init(self):
        self.lock = threading.Lock()
        self.channel = VoiceChannel()

    def _start_current(self):
        self.channel.stop()
        self.active = False
        self.update()

    def previous(self):
        self.history = True
        if self.current > 0:
            self.current -= 1
        self._start_current()

    def _current_message_is_unsaid(self):
        return self._exists(self.current) and not self.msgs[self.current].said

    def next(self, history_only=False):
        if self.active:
            if self._current_message_is_unsaid():
                if not history_only:
                    self._mark_current_as_said() # give up current message
                    self.current += 1
                else:
                    return
            else:
                self.current += 1
            self._start_current()

    def _exists(self, index):
        return index < len(self.msgs)

    def _unsaid_exists(self):
        return self._exists(self.unsaid)

    def alert(self, *args, **keywords):
        self._say_now(interruptible=False, *args, **keywords)

    def important(self, *args, **keywords):
        self._say_now(*args, **keywords)

    def confirmation(self, *args, **keywords):
        self._say_now(keep_key=True, *args, **keywords)

    def menu(self, *args, **keywords):
        self._say_now(keep_key=True, *args, **keywords)

    def info(self, lns, *args, **keywords):
        """Say sooner or later."""
        if lns:
            self.msgs.append(Message(lns, *args, **keywords))
            self.update()
        
    def _say_now(self, lns, lv=DEFAULT_VOLUME, rv=DEFAULT_VOLUME, interruptible=True, keep_key=False):
        """Say now (give up saying sentences not said yet) until the end or a keypress."""
        if lns:
            with self.lock:
                self._give_up_current_if_partially_said()
                self.channel.play(lns, lv, rv)
                while self.channel.get_busy():
                    if interruptible and self._key_hit(keep_key=keep_key):
                        break
                    time.sleep(.1)
                    self.channel.update()
                if not interruptible:
                    pygame.event.get([KEYDOWN])
                self.msgs.append(Message(lns, lv, rv, said=True))
                self._go_to_next_unsaid() # or next_current?
                self.active = False
#                self.update()

    def _mark_current_as_said(self):
        self.msgs[self.current].said = True

    def _mark_unsaid_as_said(self):
        self.msgs[self.unsaid].said = True

    def _go_to_next_unsaid(self):
        self.current = self.unsaid

    def _give_up_current_if_partially_said(self): # to avoid to many repetitions
        if self._current_message_is_unsaid() and self.channel.is_almost_done():
            self._mark_current_as_said()

    def item(self, lns, lv=DEFAULT_VOLUME, rv=DEFAULT_VOLUME):
        """Say now without recording."""
        if lns:
            with self.lock:
                self._give_up_current_if_partially_said()
                self._go_to_next_unsaid()
                self.channel.play(lns, lv, rv)
                self.active = False
                self.history = False

    def _expired(self, index):
        msg = self.msgs[index]
        if msg.has_expired():
            return True
        # look for a more recent message of the same type
        if msg.update_type is not None:
            for m in self.msgs[index + 1:]:
                if m.update_type == msg.update_type:
                    return True
        # look for a more recent, identical message
        for m in self.msgs[index + 1:]:
            if msg.lns == m.lns:
                return True
        return False

    def _mark_expired_messages_as_said(self):
        for i, m in enumerate(self.msgs):
            if not m.said and self._expired(i):
                m.said = True

    def update(self):
        self._mark_expired_messages_as_said()
        if self.channel.get_busy():
            self.channel.update()
        else:
            if self.active: # one message from the queue has just finished
                self._mark_current_as_said()
                self.current += 1
            if not self.history:
                self._go_to_next_unsaid()
            if self._exists(self.current):
                self.channel.play(*self.msgs[self.current].unpack())
                self.active = True
            else:
                self.active = False
                self.history = False

    def silent_flush(self):
        self.channel.stop()
        self.active = False
        self.current = len(self.msgs)
        for m in self.msgs:
            m.said = True

    def flush(self, interruptible=True):
        while True:
            self.update()
            if not (self._unsaid_exists() or self.channel.get_busy()):
                break
            elif interruptible and self._key_hit(): # keep_key=False? (and remove next line?)
                if self._unsaid_exists():
                    self.next()
                    pygame.event.get([KEYDOWN]) # consequence: _key_hit() == False
                else:
                    break
            time.sleep(.1)
        if not interruptible:
            pygame.event.get([KEYDOWN])

    def _key_hit(self, keep_key=True):
        l = pygame.event.get([KEYDOWN])
        if keep_key:
            for e in l: # put events back in queue
                pygame.event.post(e) # XXX: will the order be preserved?
        return len(l) != 0


voice = _Voice()
