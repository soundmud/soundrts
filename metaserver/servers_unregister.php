<?php

// Description:

// SoundRTS servers call this file to unregister from the servers list.

// The parameters are:
// - ip: the IP address of the server; only numbers, no hostname
// (optional parameter; if it is absent or empty, it will be guessed by the script)

// Example: http://jlpo.free.fr/soundrts/metaserver/servers_unregister.php?ip=000.000.000.000

// Returns:
// - if an error occurs, "error" followed by an explanation;
// - if it works, an empty page.

// End of description.


// The code starts here...

require("config.php");

// get the parameters

$rvar_ip = getenv("REMOTE_ADDR");
import_request_variables("gP", "rvar_");
if (!preg_match("/^[0-9.]{7,40}$/", $rvar_ip)) $rvar_ip = getenv("REMOTE_ADDR");

// connect to the database

$link = mysql_connect($dbhost, $dbuser, $dbpasswd)
	or die("error: connection to database failed");
mysql_select_db($dbname)
	or die("error: could not select database");

// remove old servers and servers with this IP address from the database

$time_limit = time() - 60 * 10;
$query = 'DELETE FROM soundrts_servers WHERE ip = "'.$rvar_ip.'" OR time < '.$time_limit;
mysql_query($query) or die('error: query failed: '.mysql_error());

// disconnect from the database

mysql_close($link);

?>
