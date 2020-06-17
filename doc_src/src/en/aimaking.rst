Making AIs Tutorial
===================

.. contents::

1. Introduction
---------------

This tutorial will explain the basics of creating AIs.
You'll need to edit the ai.txt file.
This file can be found on the "res" folder in the SoundRTS zip file.

2. Constants
------------

Before the "def" of the AI, you'll see some text like:
research 1, teleportation 1... Etc.
These constants will control the behavior of the AI, and can be 0 or 1.
Here are all of the constants.

- constant_attacks - The AI will constantly attack and explore the map.
- research - The AI will research the weapons and armors.

3. The "get" command
--------------------

The "get" command will take the number of the units and its names as
arguments to recruit the units.
You can define more than one unit number and type.

Example:
"get 10 footman 20 archer 10 knight"

See the "rules.txt" file for the exact unit type names.
