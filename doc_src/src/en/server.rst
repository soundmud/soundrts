Standalone server guide
=======================

.. contents::

Introduction
------------

This guide explains how to install a standalone, public server. A public server allows any player to create games.


Installation from source
------------------------

- Archive method:
    - Download the source archive of the latest release from https://github.com/soundmud/soundrts/releases/latest
    - Uncompress the archive in the folder of your choice.
- Git method:
    - to install v1.3.2:
        - git clone https://github.com/soundmud/soundrts.git
        - git checkout v1.3.2
    - later, to update to v1.3.3:
        - git fetch
        - git checkout v1.3.3
- Create an empty folder called "user" in the main folder.
- Install Python 3.7 or later.
- Start the server: python server.py
- This will generate "user/SoundRTS.ini".
- Press Control+C to close the server.
- Edit the newly created "user/SoundRTS.ini":
    - Set "login" to the name of the server.
    - Set "require_humans" to 1 if you want only games with at least 2 human players.
- Start the server: python server.py
- Make sure your server is accessible from outside.


How to make your server accessible from outside
-------------------------------------------------

In most cases you will have to configure your router to forward incoming TCP connections through port 2500 to the local IP address of your server.

You might also have to configure DHCP in the router to make sure that your server have always the same local IP address.

If you are behind a firewall, you might have to make sure that incoming TCP connections through port 2500 are allowed.


How to check if your server is accessible from outside
-----------------------------------------------------------

To check if your server is accessible from outside your local network, wait for a player to connect, or ideally ask a friend to connect from outside.

As a last resort, you can also use a port forwarding tester website (google "port forwarding tester" for example). Be cautious: I can't guarantee that this kind of website isn't malicious! The web site shouldn't require you to install a tool, for example.


The list of servers
-------------------

The list of servers is hosted by the metaserver.

As soon as your server is started, it should be automatically included in the list. That doesn't mean that your server is accessible from outside.

After being stopped, the server will disappear automatically from the list. It might take some time though.


The require_humans parameter in SoundRTS.ini
----------------------------------------------

Default value: 0

If require_humans is set to 1, the server won't let the game creator invite computers until at least two human players are registered.

Only public servers are affected by this parameter.