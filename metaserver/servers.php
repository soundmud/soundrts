<?php

// Description:

// SoundRTS clients call this script to get the servers list.

// Parameters:
// - header: string to include at the start of the reply
// (optional; used to detect 404 errors; nothing is included by default)
// (must contain only letters, numbers and underscores; max length: 20)
// - include_ports: if 1, include the port numbers in the reply
// (optional; used after 1.1-a4; 0 by default)

// Example: http://jlpo.free.fr/soundrts/metaserver/servers.php
// Example: http://jlpo.free.fr/soundrts/metaserver/servers.php?header=SERVERS_LIST
// Example: http://jlpo.free.fr/soundrts/metaserver/servers.php?header=SERVERS_LIST&include_ports=1

// Returns, for each server, a line containing, separated by the space character:
// - the UNIX time in seconds;
// - the IP address of the server;
// - the compatibility version of the server; for example: 1.0-b10o;
// - the login of the server.

// End of description.


// The code starts here...

require("config.php");

// get the parameters

$rvar_header = "";
import_request_variables("gP", "rvar_");
if (!preg_match("/^[a-zA-Z0-9_]{0,20}$/", $rvar_header)) exit("error: bad header");
if (!preg_match("/^[0-1]$/", $rvar_include_ports)) $rvar_include_ports = "0";

// print the optional header

echo $rvar_header;

// connect to the database

$link = mysql_connect($dbhost, $dbuser, $dbpasswd)
	or die("error: connexion to database failed");
mysql_select_db($dbname)
	or die("error: could not select database");

// get the servers from the database

$time_limit = time() - 60 * 10;
$query = 'SELECT time, ip, version, login, port FROM soundrts_servers WHERE time > '.$time_limit;
$result = mysql_query($query) or die('error: query failed: '.mysql_error());

// print a line for each server

while ($row = mysql_fetch_assoc($result)) {
   if ($rvar_include_ports == "0")
       echo $row["time"]." ".$row["ip"]." ".$row["version"]." ".$row["login"]."\n";
   else
       echo $row["time"]." ".$row["ip"]." ".$row["version"]." ".$row["login"]." ".$row["port"]."\n";
}

// disconnect from the database

mysql_close($link);

?>
