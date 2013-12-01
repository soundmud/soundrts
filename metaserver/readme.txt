1. Goal

These files are provided just in case the current metaserver went down for good.
As long as the default metaserver of SoundRTS is working, nobody probably needs to set up a new one.
The metaserver manages the servers list, allowing players to find game servers easily.

2. Installation

You must have a server with PHP and MySQL.
Fill in the file called config.php.
Create a folder and upload the files into this folder.
From a web browser, load the page http://your_server/metaserver_folder/init_tables.php
Remove the init_tables.php file from the server.
Remove the config.php file from your local computer (just to make sure the MySQL server password is not everywhere).

3. Client-side parameters

Edit the file called metaserver.txt and enter the new metaserver URL, including the slash at the end of the URL.
For example: http://your_server/metaserver_folder/
