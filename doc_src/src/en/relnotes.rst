Release notes
=============

.. contents::

1.3.2
-----

Changes from 1.3.1:

Main changes:

- the "choose a server" menu will include any server with a compatible server version (not only the same version) so the servers won't have to be updated as often
- compatible clients with different versions will be allowed to play together
- the "nearest" servers will appear first in the "choose a server" menu (servers with the smallest delay of response)
- the time taken to check if a server is available will be mentioned (expressed in milliseconds) in the "choose a server" menu for comparison
- the unavailable servers won't appear in the "choose a server" menu

Minor changes:

- slightly decreased the verbosity of server.log
- improved the standalone server guide (still not perfect though)
- added "release notes" to the documentation

1.3.1
-----

Changes from 1.3.0:

- probably fixed: the game wouldn't start on Windows 7 (ImportError: DLL load failed while importing _socket)
- fixed: sometimes the game wouldn't start until the folder "gen_py" in "appdata\local\Temp" is deleted (AttributeError: module 'win32com.gen_py...' has no attribute 'CLSIDToClassMap')
- fixed: vcruntime140.dll could be missing
- fixed: couldn't get the list of servers
- fixed: pressing A will behave like before and pressing Control+A will only select inactive orders

1.3.0
-----

Changes from 1.2-c12:

Main changes:

- only walls and gates can be built on exits (or any building "buildable on exits only")
- now a tower can be built only at the center of a sub-square, and only one tower per sub-square. The location of a tower can be selected in several ways:

  - in zoom mode: selects the current sub-square (must be free)
  - in square mode: selects any free sub-square, starting with the central one
  - if any object is selected: selects the enclosing sub-square (must be free)

- now the screen reader is the default TTS

Technical changes:

- migrated to Python 3
- replaced all TTS with accessible_output2 (patched to support Linux)

Bugs fixed:

- couldn't control a resurrected unit which was in a group
- a worker who postponed building or gathering to eliminate an intruder wouldn't move back to its task and would complete it in place
- a unit could see a plateau from below
- a unit couldn't see diagonally
- couldn't select a square as a target for building a gate (a free exit will be selected)

Interface improvements:

- zoom mode: validating a build order of a wall (or a gate) without selecting a specific target will automatically select the local exit (if it isn't blocked)
- tab will select any enemy first
- pressing escape when a target is selected will select the current square
- bug fixed: now entering or exiting zoom mode will select the mini-square or square as a target (instead of keeping the selected target)
- added commas in some messages (for clarity)
- shorter enemy summary
- bug fixed: would say "building site" and not the type of building
- bug fixed: in zoom mode, a default order for a building didn't set the rallying point to the sub-square but to the square
- bug fixed: a paused game wouldn't quit
- bug fixed: pressing Space will tell the exact orders even when some units have different orders (This is very useful to check how many workers are gathering gold, wood, etc (by pressing D). This could be useful to know how many units in a group are moving and how many have arrived. Pressing Control + Shift + S will give a complete summary of the orders of soldiers and workers.)
- in building mode, tab will select meadows before exits
- the description of a patrol order will recapitulate all the waypoints
- bug fixed: pressing Tab would select blocked exits
- bug fixed: it is no longer possible to build another wall on the same exit
- zoom mode: if no building land is found while a build order has been validated on a sub-square, an error will be raised (instead of searching for a building land in the enclosing square