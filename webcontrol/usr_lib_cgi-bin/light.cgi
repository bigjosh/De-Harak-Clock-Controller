#!/bin/bash
echo "Content-type: text/html"
echo ''
echo 'Query=' $QUERY_STRING

#this is called from the ajax on the controller webpage
#it pipes the commands into a pipe waiting that was started automatically at boot

pipe=/tmp/clockcommands

#RUN webcontrol/install.sh to copy this file to right place after changes

#TEST WITH:
#QUERY_STRING="clockmode&000000&when=1519847424544" (nope that doesnot work)
#sudo su www-data -s /bin/sh -c '/usr/lib/cgi-bin/light.cgi "Query= ticktest&000000&when=1519842067266"'

# make sure multipule copies of this script dont step on each other...


if [ "$QUERY_STRING" == "leases"* ]; then

        echo "<pre>"
        cat /var/lib/misc/dnsmasq.leases
        echo "</pre>"

else
    #pass command to the command reader

    echo "$QUERY_STRING" >$pipe


fi

echo "GOT:$QUERY_STRING" >> /tmp/light.log
echo 'CGI Color set<br>'

