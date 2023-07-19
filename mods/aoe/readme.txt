
Starting from this version, the soldier restraint has been shaped

Update.
Added archer can be upgraded to crossbowman, crossbowman can be upgraded to arbalester (Turk has no crossbow).

Crossbowman
cooldown 1.5
damage 4.25
vs spear +2.55 and vs heavy infantry damage +11
range 5
hp 35
speed 1.

arbalester
cooldown 1.5
damage 5.4
vs spear + 2.7 vs heavy_infantry + 12
range 5
hp 40.


Added upgrade routes for skirmisher, elite_skirmisher, imperial_skirmisher (Turk cannot be upgraded imperial_skirmisher).)

skirmisher
cooldown 2.5
damage 1.8
vs archer_type + 2.7 vs cavalry_archer and spear + 2.7
range 4
armor 1.5
hp 30
speed 1
minimal_range 1.

elite_skirmisher
cooldown 2.5
damage 2.7
vs archer_type +3.6 vs cavalry_archer and spear +2.7
range 5
armor 2.5
hp 35
minimal_range 1.

imperial_skirmisher
cooldown 2.5
damage 3.6
vs archer_type + 4.5 vs cavalry_archer and spear + 2.7
range 5
armor 3
hp 35
minimal_range 1.


Add upgrade routes for Mangonel, Onager, Siege_Onager.
Mangonel
cooldown 6
damage 40
range 7
sight_range 9
damage_radius 0.25
hp 40
speed 0.6
minimal_range 3
vs building damage +35, vs cavalry_type 8

Onager
cooldown 6
damage 50
range 8
sight_range 10
hp 60
minimal_range 3.
vs building damage +45, vs cavalry_type 8


Siege Onager
cooldown 6
damage 75
range 8
sight_range 10
hp 70
minimal_range 3.
vs building damage +55, vs cavalry_type 8

Turk adds siege_ram.
siege_ram
damage 2
cooldown 5
armor -3
shield 80
hp 200
speed 0.6
damage_radius 0.25
carry 6.
vs building damage +200


This mod tries to be as relatively balanced as possible, so that each unit has its own use.

One of the features of this mod is that units can switch between melee and long-range modes, for example, light_infantry can switch between archer and melee infantry.

For example, light_infantry can be switched to archer and melee infantry, and light_cavalry can be switched to cavalry_archer and melee mode.
The second feature of the mod is that the units have more obvious restraint relationships, with heavy_infantry restraining melee cavalry and melee cavalry restraining siege_equipment.

siege_equipment, rifle archer grams heavy infantry and gun and spear class, siege_equipment grams all archers, such as cavalry_archer

archer are restrained by siege_equipment.

The game's units are divided into the following categories.

light_cavalry: contains two types of archers and melee mode, speed is often 1.5 meters per second

heavy_infantry: hp, damage and defense are higher than light_infantry, but the travel speed is slower, restrained by archer.

light_cavalry: the most mobile cavalry class, can switch to cavalry_archer and melee mode against the enemy according to the actual situation, due to the high mobility and speed.

The light_cavalry: the most mobile cavalry class, you can switch to cavalry_archer and melee mode to fight the enemy according to the actual situation.

But it should be noted that the attack power of cavalry_archer will be greatly reduced, but the player can try to make a release through the operation of the mandatory command with high mobility.

But note that the cavalry_archer's attack power will be greatly reduced.

At the same time, the light_cavalry, middle_cavalry or heavy_cavalry all have a fairly wide sight_range and are highly mobile, so they are often used as scouts as well.

They are often used as scouts at the same time.
The cavalry's vision can be enhanced with each upgrade of the base.
Light cavalry has a speed of 2.5 meters per second, and can hit 5 meters per second with an upgraded horse speed and 45 points of hp.

middle_cavalry:, hp is higher than light_cavalry, speed is slightly slower than light_cavalry, hp 75

heavy_cavalry: hp, armor and damage are much higher than the above two cavalry types, speed is slightly slower than middle_cavalry, usually requires a large

heavy_cavalry: hp, armor and damage are much higher than the above two cavalry types, slightly slower than middle_cavalry, and usually requires a large number of guns and spears or heavy_infantry to target. heavy_cavalry costs more, hp 110-120.

siege_equipment: usually has a longer attack range and more damage, but the downside is that after breaking into the minimum range of the type, the soldier will no longer

work and be at the mercy of others.

Flying class: Another class that is more mobile and can ignore walls to go directly to their destination, this type of unit often has to be targeted with foot archers.

This type of unit often has to be targeted with the rifle bow, the general ground target can not hit, hp 40-60.

Auxiliary class: the type of unit that can assist other units in combat, such as the priest's healing ability, hp60 points.

Boat class.
As the name implies, water combat soldier type.


The following describes the specific parameters of each unit type.

light_infantry class.
Public attributes.
Foot archer mode.
Armor 0
Speed 1.5ms
sight_range 6
Ranged 4
hp30.
Damage3.2
Cooldown 1.5
vs spear + 2.4 vs heavy_infantry 11
Volume 1

Melee mode.
Armor 0
hp45
Damage 6
Cooldown 1.5
sight_range 6
Size 1


pike and spear class.

Spearmen.
hp45
sight_range 6
Armor 0
Damage 3
Cooldown 2
vs Cavalry +15

pikemen
hp45
Damage 4
vs Cavalry + 22
Cooldown 2

Turk Shooter
hp30
Ranged 6
sight_range8
Cooling 3
Damage 8
Invisible units


Heavy infantry class.

Public Attributes.

hp70
sight_range 6
Armor 0.5
Damage 13
vs Cavalry +45
cooldown 1.5
Volume 1


Byzantine sword and shield soldier.
armor 1


Varangian Guard.
damage 12


light_cavalry class.
Public Attributes.
Melee mode.
hp60
Speed 2.5
sight_range 6-10
Damage 7
vs doctor + 10, vs heavy_infantry -3.5
Cooldown 1.5
Volume 2

cavalry_archer mode.
hp50
Range 4
sight_range6-10
Damage3
vs spear +1
Cooldown 1.5
Volume2


turk_blade_cavalry.
cooldown 1.3


middle_cavalry class.
Public attributes.
hp80
sight_range 6-10
Speed 2.5
Damage 7
Cooldown 1.4
vs doctor + 12 vs heavy_infantry -3.5
Volume2



Heavy cavalry class.
Public Attributes.
Melee mode.
Speed 2
hp100
Damage 12
Cooling 1.3
vs doctor 14
Armor 0.5
Volume 3

Flak mode.
hp60
Ranged 5
sight_range7
Cooling 1.5
Damage3.5
vs spear + 1
Armor 0


Siege equipment.


Mangonel.
Ranged 7
Minimum range3
sight_range9
Cooling 6
Damage 40
Impact radius 0.25
vs building +35, vs cavalry_type 8

tang_transport_truck
hp100
Speed 2
sight_range 6
Transport capacity 10

Flight class.
Public Attributes.
Speed 3
sight_range 6

tang_dragon.
hp30
Range4
Cooling4
Damage4
Impact radius 1

turk_wolf:
hp45
Attack range1
Cooldown 1.5
Damage 7.5
Can detect invisible units

Turkic finch.
hp20
Attack range 0.8
Cooling 1
Damage 1
Can only attack aerial targets.

Byzantine double-headed eagle.
hp55
Attack range 1
Cooldown 2
Damage 12
Can detect invisible units

Auxiliary class.
Public Attributes.
hp60
Speed 1
Range 6
sight_range8
Volume 2

tang_taoist_priest.
Healing ability 5
Cooling 1.5
Damage 5.5
Can use thunder, lobby, super_dragon.


Turkic Shaman.
Cooldown 1.5
Damage 5.5
Can use rain, super_flying_wolf, compel.

Byzantine Priest.
Healing ability 5
Can use resurrection, conversion.

Ship class: (omitted)


Architecture class.

Buildings with the ability to detect invisibility include the Tang Empire's sentry towers and citadels, Turkic sentry towers, Byzantine guard towers and forts.

crossbowtower.
Damage 20-22
Cooldown 6
Damage radius 0.25
hp800
Ranged10-12
sight_range14



turk_ambush_circle
Upgraded by Turk's sentry tower, it is invisible, with 20 light_cavalry and 20 archer inside, can wait for the enemy to pass by and release them

The enemy can be caught by surprise.


Byzantine catapulttower
hp800
Damage 20
Cooling 10
Ranged12
sight_range14
Damage radius 0.25

Skill Class.

thunder.
Damage 100-150
Release distance 12

Rain.
Initial ability is healing, recover 5 points per second, upgrade to add camouflage effect.
Release distance 24