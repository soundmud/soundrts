
Modding guide
:::::::::::::

.. contents::

mods
----

The rules of the game and the aspect of the game can be changed by mods.

A mod is a folder potentially containing rules.txt, ai.txt, ui (and their localized versions). The structure of the tree is the same as the "res" folder structure.

The mods are stored in the "mods" folder of the main folder or the "mods" folder of the user's folder. To be activated, a mod must be referenced in the "mods =" parameter in SoundRTS.ini.
For example: mods = soundpack,mymod,my_other_mod

The rules.txt file will patch the default file. For example, a rules.txt file containing these 2 lines: "def peasant" and "decay 20" will cause any peasant to disappear after 20 seconds.

clear
>>>>>

To replace rules.txt or style.txt instead of patching it, use the "clear" command at the top of your file. This doesn't work with ai.txt,
and isn't needed anyway, because in ai.txt the def command rewrites the AI definition.

is_a
>>>>

While in style.txt "is_a" is a way to inherit all the properties of another definition,
in rules.txt, "is_a" is also used to make sure that a keep or a castle will allow what a town hall would allow.

Note: the inheritance trees in style.txt and in rules.txt don't need to match.

the rules
---------

Since SoundRTS 1.1, the rules of the game are stored in a file called rules.txt.

faction
>>>>>>>

Each faction is defined in rules.txt . For example::

	def orc_faction
	class faction

Note: the "orc_faction" name ends with "_faction" just to avoid name clashes. This "_faction" suffix is not mandatory as long as the name is unique.

unit
>>>>

Note: a unit can also be a building.

count_limit
===========

New in SoundRTS 1.2 alpha 10.

`count_limit <value>`

The default value is 0 (no limit).
When the limit is active, a unit type which reaches the limit cannot be trained,
built, summoned, raised, resurrected, or added by a trigger (add_unit).
Conversion is unaffected though.

is_ballistic
============

New in SoundRTS 1.2 alpha 9.
Modified in SoundRTS 1.2 alpha 10.

`is_ballistic 1`

The unit have a range bonus if the altitude of the target is lower.

is_teleportable
===============

New in SoundRTS 1.2 alpha 9.

`is_teleportable 1`

The unit (or building) is affected by the teleportation effect or the recall effect.

hp_regen
========

New in SoundRTS 1.2 alpha 11

`hp_regen <hit points regeneration rate>`

For example, with "hp_regen 0.15", the unit regains 0.15 hit points per second.

mana_start
==========

New in SoundRTS 1.2 alpha 10.

`mana_start 50`

In the example, the unit will start with 50 mana instead of mana_max. The default value for mana_start is 0. If mana_start is 0 or negative, mana_max is used instead.

provides_survival
=================

New in SoundRTS 1.2 alpha 9.

`provides_survival 1`

Having at least one unit (or building) with "provides_survival" equal to 1 prevents a player from losing in a multiplayer game (not in a single player campaign). The affected trigger is "no_building_left". By default only the buildings have this property set to 1. Construction sites have this property set to 0 and it cannot be changed.

storage_bonus
=============

`storage_bonus <bonus for resource 0> <bonus for resource 1> ...`

For example, "storage_bonus 0 1" will cause a +1 bonus for wood (the second resource type).

The bonus goes to the owner of the unit.
The bonus doesn't stack: only the highest bonus will apply for each resource type.

damage_vs
=========

(damage versus specific units)

`damage_vs [<list of type names> <damage>] ...`

Defines a specific damage against some unit types.
The default value is defined in unit.damage.

Example of a type of pike man that would be more efficient against a knight
 and less efficient against a footman or a peasant:

`damage 2 ; default damage`

`damage_vs knight 7 footman peasant 1`

ability
>>>>>>>

effect
======

`effect <effect type> [parameters]`

Default value: (none)

An effect is a property of an ability. When an ability is used by a unit, the effect will take place unless no effect type has been mentioned.

Additional properties can modify an effect: effect_target_ and effect_range_.

apply_bonus
^^^^^^^^^^^

`effect apply_bonus <property name>`

Increases the property of the affected units. The value is defined in the property of the unit called "<property name>_bonus".
For example, "effect apply_bonus damage" will look for a property called "damage_bonus" in the definition of each affected unit.
This way, units benefiting from the same upgrade can have different bonus values.

bonus
^^^^^

`effect bonus <property name> <value>`

Increases by the indicated value the property of the affected units.

At least the following properties should work: damage, armor, range, heal_level, speed, hp_max (old units won't have their hp updated to hp_max though).
food_cost and food_provided probably don't work correctly.

conversion
^^^^^^^^^^

`effect conversion` (no parameter)

Moves the target to the caster's army.

If the target isn't an enemy of the caster, nothing will happen.

Allowed values for the related properties:

* effect_target: ask
* effect_range: square, nearby, anywhere

**TODO: add a <limit> so units in a targeted square are chosen (instead of having to target a unit)**

raise_dead
^^^^^^^^^^

`effect raise_dead <life span (in seconds)> <unit types and numbers>`

Creates the required units in the targeted square from the corpses in the square, in the order of the units list. If there are not enough corpses, the end of the list will not be created. The units will disappear after <life span> seconds, unless <life span> is set to 0.

If no corpse is in the targeted square, the order won't be executed.

Allowed values for the related properties:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

recall
^^^^^^

`effect recall` (no parameter)

Similar to teleportation. Teleports the player's units from the targeted square back to the caster's square. Buildings are unaffected. Allied units are unaffected too.

If no unit is in the targeted square, the order won't be executed.

Allowed values for the related properties:

* effect_target: ask, random
* effect_range: nearby, anywhere

resurrection
^^^^^^^^^^^^

`effect resurrection <limit>`

Resurrects the corpses of the caster's army lying in the targeted square, with a maximum of <limit> resurrected units. The oldest corpses are resurrected first. The hit points are restored to one third of their maximum.

If no corpse of a unit in the same army is in the targeted square, the order won't be executed.

Allowed values for the related properties:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

summon
^^^^^^

`effect summon <life span (in seconds)> <unit types and numbers>`

Creates the required units in the targeted square and adds them to the caster's army. The summoned units will disappear after <life span> seconds, unless <life span> is set to 0.

Allowed values for the related properties:

* effect_target: self, ask, random
* effect_range: square, nearby, anywhere

teleportation
^^^^^^^^^^^^^

`effect teleportation` (no parameter)

Moves the player's units in the caster's square to the target square. Buildings are unaffected. Allied units are unaffected too.
   
If the destination is the same as the caster's square, nothing will be done.

Allowed values for the related properties:

* effect_target: ask, random
* effect_range: nearby, anywhere

effect_target
=============

`effect_target <selection method>`

Determines how the target will be selected.

Default value: self

Possible values:

* self: the target will be the caster (or the location of the caster if the target must be a place)
* ask: the user interface will ask for a target
* random: the game will choose a random square as a target

effect_range
============

`effect_range <distance>`

Determines the distance between the caster and the target.

Default value: 6

Special value: inf (infinite)

If the current distance is greater than the required distance, the caster will try to move to a closer place and use the ability from there.

effect_radius
=============

`effect_radius <distance>`

Determines the radius of the area of effect. The center of the area is the target.

Default value: 6

Special value: inf (infinite)

style
-----

The style is defined in "ui/style.txt" and in the localized version of "style.txt".

shortcut
>>>>>>>>

Simple orders, building orders, training orders, orders using an ability can be given with a shortcut, if a shortcut is defined.

To define a shortcut, define a "shortcut" property followed by the corresponding letter. The letter must be in lowercase.

If the order is a simple order, the shortcut must be defined by the order (ex: patrol).
If the order is a complex order (train, build, use an ability), the shortcut must be defined by the second part of the order.
For example, define an "m" shortcut for the meteor ability so the mage will have the "m" shortcut to cast meteors.