# Problem with SDL (at least the one included in Pygame 1.9.1),
# at least on Windows 10:
# when focusing back with Alt+Tab,
# or when starting the game with a Control+Alt desktop shortcut,
# the modifier keys stick until they are pressed and released again.
#
# This problem is mentioned there:
# https://github.com/pygame/pygame/issues/436
#
# The workaround used here is to regularly update the modifier keys
# with the results of GetAsyncKeyState(vkey).
#
# GetAsyncKeyState function:
# https://msdn.microsoft.com/en-us/library/windows/desktop/ms646293.aspx
# Virtual-Key Codes:
# https://msdn.microsoft.com/en-us/library/windows/desktop/dd375731.aspx

import os


if os.name != "nt": # Windows
    def eventually_fix_modifier_keys(): pass
    def get_modifier_keys_status(): return ""
else:
    from pygame import KMOD_LCTRL, KMOD_LALT, KMOD_RALT, KMOD_RCTRL
    from pygame.key import get_mods, set_mods
    from ctypes import windll


    GetAsyncKeyState = windll.user32.GetAsyncKeyState

    VK_LCONTROL = 0xa2
    VK_RCONTROL = 0xa3
    VK_LMENU = 0xa4
    VK_RMENU = 0xa5

    _modifiers = (
        (VK_LCONTROL, KMOD_LCTRL),
        (VK_LMENU, KMOD_LALT),
        (VK_RMENU, KMOD_RALT),
        (VK_RCONTROL, KMOD_RCTRL),
        )

    def eventually_fix_modifier_keys():
        """update the modifier keys"""
        for vkey, kmod_mask in _modifiers:
            win = GetAsyncKeyState(vkey)
            sdl = get_mods() & kmod_mask
            if (win and not sdl) or (not win and sdl):
                set_mods(get_mods() ^ kmod_mask)

    def get_modifier_keys_status():
        """display-friendly status of the modifier keys"""
        s = ""
        for vkey, kmod_mask in _modifiers:
            win = GetAsyncKeyState(vkey)
            sdl = get_mods() & kmod_mask
            s += "*" if sdl else "."
            s += "*" if win else "."
            s += " "
        return s
