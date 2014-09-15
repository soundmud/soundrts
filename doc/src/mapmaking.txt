Map making guide
================

.. contents::

Introduction
------------

The best way to start is probably to make a multiplayer map and test it against the computer.

Multiplayer maps
----------------

Where to store a new multiplayer map
""""""""""""""""""""""""""""""""""""

If you are allowed to write in the folder where SoundRTS (or SoundRTS test) is installed,
then you can store your first multiplayer map in the "multi" folder.

If you are not allowed to write in the program files folder because you work in non-admin mode, you can store your working map file in the "multi"
folder in "C:\\Documents and Settings\\Your Login\\Application Data\\SoundRTS". This folder is created the first time you start SoundRTS.
Another solution is to install SoundRTS in a folder where you are allowed to write, and to work in the folder mentionned in the previous paragraph.

How to edit a map
"""""""""""""""""

Open the file with a text editor.
Write in lower case, even if case will be probably ignored anyway.

How to test a map
"""""""""""""""""

To test a map, start SoundRTS and go to the single player menu. You can play against the computer on multiplayer maps.
The map is reloaded each time you start a game, so you don't need to restart SoundRTS to test the modifications.
A useful key combination is Control Shift F2: if you are the only human on the map, you will be able to examine the whole map (no fog of war).

How to find and remove an error
"""""""""""""""""""""""""""""""

If, when you start the map, you get the message: "server error" and go back to the server menu, then the details of the error are in a file called "maperror.txt". This file is in your default temporary folder (for example "C:\\Documents and Settings\\Your Login\\Local Settings\\Temp\\soundrts") or in the SoundRTS folder.

In the same directory you may find additional (but cryptic) information in "server.log" or in "client.log".

If you still don't understand where the error is, feel free to contact me, directly or at the soundRTSChat list.

Comments
""""""""

The lines that start with a semicolon are comments. Comments are ignored at runtime.
Everything after a semicolon until the end of the line is a comment too.

Basic properties
""""""""""""""""

Title
'''''

"title 4018 5000" means: "the title of the map is the sound 4018 followed by the sound 5000".

Objective
'''''''''

"objective 145 88" means: "the objective of the map is the sound 145 followed by the sound 88".

Nb_players_min and nb_players_max
'''''''''''''''''''''''''''''''''

"nb_players_min 2" means: "2 players are needed to start the game."
"nb_players_max 4" means: "4 players in this map is a maximum."

Global_food_limit
'''''''''''''''''

New in version beta 9e.

Update in version beta 10 o: this food limit is not divided among the players anymore.

"global_food_limit 200" means: "Every player cannot have more than 200 food, even if he builds more farms."

Defining the terrain
""""""""""""""""""""

Square_width
''''''''''''

"square_width 12" means: "the square width is 12 meters".
You shouldn't modify this parameter, since objects may be inaudible if they are too far.

Nb_lines and nb_columns
'''''''''''''''''''''''

"nb_lines 7" mean: "the grid has 7 lines".
"nb_columns 7" mean: "the grid has 7 columns".
The limit for columns is 26 and there is no limit for lines, but the actual limit is probably not far from 26 anyway, because of performance.
Warning: nb_rows is deprecated and has the same meaning as nb_columns.

West_east_paths and south_north_paths
'''''''''''''''''''''''''''''''''''''

"west_east_paths a1 c1 d1 f1" means: "add a path from a1 to b1, from c1 to d1, from d1 to e1, and from f1 to g1".
You only need to give the west-most square of the path.
"south_north_paths a1 a3 a4 a6" means:  "add a path from a1 to a2, from a3 to a4, from a4 to a5, and from a6 to a7".
You only need to give the south-most square of the path.

West_east_bridges and south_north_bridges
'''''''''''''''''''''''''''''''''''''''''

Bridges work exactly like paths.

General case: west_east and south_north
'''''''''''''''''''''''''''''''''''''''

"west_east road a1 c1 d1" means: "add an exit with the 'road' style from a1 to b1, from c1 to d1, from d1 to e1"

'road' must be defined in style.txt

Note: "west_east_paths" is the same as "west_east path"

Note: "south_north_bridges" is the same as "south_north bridge"

Goldmines, woods, and other resource deposits
'''''''''''''''''''''''''''''''''''''''''''''

"goldmine 150 a2 b7 g6 f1" means: "add goldmines with 150 gold at a2, b7, g6 and f1".

"wood 150 a2 b7 g6 f1" means: "add woods with 150 wood at a2, b7, g6 and f1".

"goldmine" and "wood" are defined in rules.txt as resource deposits ("class deposit").

The old plural keywords ("goldmines" and "woods") are still working.

Nb_meadows_by_square
''''''''''''''''''''

"nb_meadows_by_square 2" means: "auto fill the map with 2 meadows in each square".

Additional_meadows
''''''''''''''''''

"additional_meadows a2 b7 g6 f1" means: "add 1 meadow in the squares a2, b7, g6 and f1".
"additional_meadows a2 a2 g6" means: "add 2 meadows in a2 and 1 meadow in g6".

Remove_meadows
''''''''''''''

remove_meadows do the opposite of additional_meadows.

High_grounds
''''''''''''

New in SoundRTS 1.2 alpha 9.

"high_grounds a2 b7" means: "a2 and b7 will have a higher altitude"


Defining the starting resources of the players
""""""""""""""""""""""""""""""""""""""""""""""

Case 1: same resources for everybody
''''''''''''''''''''''''''''''''''''

Use the following commands in combination:

starting_resources
..................

"starting_resources 10 10" means: "each player starts with 10 gold and 10 wood."

starting_units
..............

"starting_units townhall farm peasant" means: "each player starts with 1 townhall, 1 farm and 1 peasant."

"starting_units townhall 2 farm peasant" means: "each player starts with 1 townhall, 2 farms and 1 peasant."

Since SoundRTS 1.1, starting_units can also contain:

- upgrades and research: "starting_units u_teleportation" means: "each player has teleportation already researched."
- forbidden units, buildings, abilities, upgrades/research (they won't appear on the menu):

  - "starting_units -u_teleportation" means: "each player cannot research teleportation."
  - "starting_units -a_teleportation" means: "each player cannot use teleportation."

starting_squares
................

"starting_squares a2 b7 g6 f1" means: "the starting squares of the players are a2, b7, g6 and f1."

The starting units and buildings will be created in these squares.

Case 2: different resources depending on the player
'''''''''''''''''''''''''''''''''''''''''''''''''''

player
......

The "player" command defines a starting point that might be used by a human player or by a computer AI (in multiplayer games).

This command can be repeated several times in a multiplayer map.

"player 5 10 -townhall a1 townhall peasant c1 footman"
means: "a player will start with 5 gold, 10 wood, won't be allowed to build a town hall, will have a townhall and a peasant at A1, a footman at C1.

computer_only
.............

The "computer_only" command defines a starting point that will always be played by a computer AI. This AI will be hostile to any other player or AI.

This command can be repeated several times but be careful: too many AI can slow the game.
So use one AI if these units are not supposed to fight each other (several dragons all over the map for example).

computer_only 0 0 a3 dragon b1 dragon
means: "add a computer AI with 0 gold, 0 wood, a dragon at A3 and a dragon at B1."

Types list
''''''''''

Here are some correct names for types used in starting_units_, player_ and computer_only_ .
For a full list, examine the rules.txt file: the name is just after the "def" statement.

- units: peasant footman archer knight catapult dragon mage priest necromancer
- buildings: farm barracks lumbermill blacksmith townhall stables workshop dragonslair magestower
- abilities: a_teleportation
- upgrade/research: u_teleportation melee_weapon

#random_choice,  #end_choice and #end_random_choice
"""""""""""""""""""""""""""""""""""""""""""""""""""
(new in beta 9g)
This preprocessor directive chooses randomly between 2 or more choices delimited by #random_choice,  #end_choice and by #end_random_choice for the last choice.
Each choice consists in zero or more lines.
More than one #random_choice directives can be used in a map file, but they cannot be nested.

This can be used for example to place random resources. For example:
#random_choice
goldmines 500 e2 c6 b3 f5
#end_choice
goldmines 500 d2 d6 b4 f4
#end_choice
goldmines 500 c2 e6 b5 f3
#end_random_choice
The preceding lines mean: "add a goldmine at e2, c6, b3 and f5, or at d2, d6, b4 and f4, or at c2, e6, b5 and f3". This way, the resources are balanced (if I didn't make a mistake of course). This is only an example.

The title of the map and the number of players cannot be changed this way because the preprocessor is run when the map is loaded (that is to say: long after the single player menu is loaded).

Advanced multiplayer maps: how to change the rules and the aspect of the game
-----------------------------------------------------------------------------

Map structure
"""""""""""""

The advanced map is a folder containing a file called "map.txt" with the content of a usual map, and most files and folders that you find in the "res" folder:
rules.txt, ai.txt, the ui folders and their content.

Note: at the moment, in a map or a campaign folder, the localized version of style.txt (for example: ui-fr/style.txt) isn't loaded.
Localized sounds are loaded though.

Single player campaigns
-----------------------

Where to store a new single player campaign
"""""""""""""""""""""""""""""""""""""""""""

If you are allowed to write in the folder where SoundRTS (or SoundRTS test) is installed, then you can store your first campaign in the "single" folder.

If you are not allowed to write in the program files folder because you work in non-admin mode, you can store your working map file in the "single"
folder in "C:\\Documents and Settings\\Your Login\\Application Data\\SoundRTS". This folder is created the first time you start SoundRTS.
Another solution is to install SoundRTS in a folder where you are allowed to write, and to work in the folder mentionned in the previous paragraph.

Structure of the campaign folder
""""""""""""""""""""""""""""""""

The name of the campaign folder will be used by the single player menu. Official campaigns will have their own title in the "ui" folder.
The folder contains chapter files. It also contains files and folders imitating the structure of the "res" folder: rules.txt, ai.txt, ui...

Required mods file
''''''''''''''''''

New in SoundRTS 1.2 alpha 10.

A campaign can define which mods it requires. The required mods will be automatically loaded.

The required mods are defined in a file called "mods.txt", in the campaign folder:

- the file is a comma-separated list of mod names;
- if the file doesn't exist, the current mods will be kept;
- if the file is empty, the "vanilla" game will be loaded.

Chapter files
'''''''''''''

Chapter files are text files called "0.txt", "1.txt", "2.txt", etc. When a campaign is started for the first time, only the chapter 0 is available. When a chapter is finished, the next chapter can be run. The number of the higher chapter available is automatically stored in the player's configuration file called campaigns.ini.

A chapter file describes a mission chapter or a cut scene chapter.

There must be at least one chapter file, called "0.txt".

Syntax of a chapter file
""""""""""""""""""""""""

A chapter is a mission or a cut scene.

Syntax of a mission chapter file
''''''''''''''''''''''''''''''''
A mission file is not very different from a multiplayer map.
The advanced map structure is also allowed: in that case, the folder name is the number of the chapter.

The following commands are not used in a single player mission: nb_players_min, nb_players_max, starting_squares, starting_units, starting_resources.

Intro
.....

Note: a number can represent a text message defined in tts.txt (new in SoundRTS 1.2 alpha 9).

Example: "intro 7500 7501 7502" means: "before the game starts, play 7500.ogg, 7501.ogg and 7502.ogg (or text if defined in tts.txt)".
The intro command defines a sequence of sounds and texts that will be played before the game starts. When the player presses a key, the next element in the sequence is played. An intro can be for example a title with music, then a scene with a discussion between characters, then a briefing. After the intro, the game will tell the objectives of the mission.

Add_objective
.............

"add_objective player1 1 7000" means: "add objective number 1 with the sound 7000.ogg"

All the objectives must be completed to win a mission. If a primary objective fails, for example when an important character dies, the mission is aborted.

Objective_complete (action in a trigger)
........................................

This action can only be included in the action part of a trigger.

"objective_complete 1" means: "now objective 1 is complete"

Trigger example:

"trigger player1 (has barracks) (objective_complete 2)" means: "add the following trigger for player1: if he has at least 1 barracks then the objective 2 is completed"

Timer coefficiency
..................

A timer coefficient can be used to measure time for triggers in a given block. 

For example, if you know that you want all of your triggers to happen in given half a minute blocks, you could set your timer coefficient to 30 like so.

"timer_coefficient 30"

Whenever this amount of time elapses, the timer counter will increment (increase by 1). You can then bind triggers to the timer reaching a given number. For example, if you wanted to make reinforcements appear on the map after 90 seconds (3 increments of 30 seconds), you would do the following. 

"trigger player1 (timer 3) (add_units a1 10 footman)" ; after three timer ticks, give the player 10 footman at a1

Cut_scene (action in a trigger)
...............................

Note: the distinction between streaming sounds and preloaded sounds have been removed in SoundRTS 1.2. All the sounds are loaded in advance.

Note: a number can represent a text message defined in tts.txt (new in SoundRTS 1.2 alpha 9).

A cut scene can be triggered in the middle of a game: when something is discovered, when reinforcements arrive, etc.

"cut_scene 7500 7501" means: play the cut scene made up of the sounds 7500 and 7501.

Trigger example:

"trigger player1 (has_entered d5) (cut_scene 7500)" means: "add the following trigger for player1: if he has entered the square d5, then play the cut scene made up of the sound 7500.ogg"

Timer and timer_coefficient (condition in a trigger)

"timer_coefficient 60"

'trigger player1 (timer 2) (cut_scene 7500)" means: "after 2 minutes (2 x 60 seconds) play the 7500.ogg sound file."

AI orders
..........

It is possible to control the computer's actions in a mission, to add some challenge. You will have to do this by directly making their units take orders at given triggers. 

For example, we can make the AI forces at A1 move to the known player location at A3, who will engage player forces as they encounter them. Here, we will launch an attack with 10 footman on the player.

"timer_coefficient 60"

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1)))"

The placement of brackets is important here, to encapsulate the right commands in the right parts of this trigger. If for some reason your trigger isn't seeming to work, try double checking your brackets.

It is also possible to queue up orders for the given units to follow. In this next scenario, lets imagine the player has their base spread over a1 and b1. We would then need to tell the footmen to go to b1 once they've finished with a1. We would do that like so. 

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1)))"

Finally, if you want the AI units to go into "auto_attack" mode, where they will hunt down any surviving player units after mopping up their base, you can do this as well. 

"trigger computer1 (timer 1) (order (a3 10 footman) ((go a1) (go b1) (auto_attack)))"

You can use orders to make the computer train up its own units, too, which you can then make the subject of later orders. Here, we will tell the computer barracks to immediately train up another 10 footmen to replace the ones we're about to send to attack the player. 

trigger computer1 (timer 0) (order (a1 barracks) ((train footman) (train footman) (train footman))) ; and so on and so on until you have 10 train footman orders

Note that each training order has to be separate, you cannot do the following: (train 10 footman)

This is not the only way to increase the amount of units the computer player has at its disposal, you could also use the add_units order as shown here.

trigger computer1 (timer 0) (add_units a1 10 footman)

However, this is immediate and doesn't offer the player any way to influence this event. In the other scenario, the player can stop the computer having its next batch of footmen by destroying the barracks used to train them. This way, these footmen will appear regardless.

Syntax of a cut scene chapter file
''''''''''''''''''''''''''''''''''

Note: the distinction between streaming sounds and preloaded sounds have been removed in SoundRTS 1.2. All the sounds are loaded in advance.

Note: a number can represent a text message defined in tts.txt (new in SoundRTS 1.2 alpha 9).

A cut scene chapter is an interruptible sequence of sounds. When the cut scene chapter has been played, the next chapter is unlocked.
Do not confuse with shorter cut scenes run by a trigger during a mission when a condition is met (discovery of a square for example), or with the mission's introduction (or briefing).

The cut scene chapters have only 3 lines. For example:
cut_scene_chapter
title 7000
sequence 7500 7501 7502

The first line is a keyword used to tell the game that this chapter is a cut scene and not a mission.
The title line is used in the campaign menu.
The sequence line means: "play the sound 7500.ogg followed by 7501 and 7502; if the player presses a key, skip the current sound and play the next one." 