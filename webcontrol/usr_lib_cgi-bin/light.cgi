#!/bin/bash
echo "Content-type: text/html"
echo ''
echo 'Query=' $QUERY_STRING ' <BR>'

#this is called from the ajax on the controller webpage
#it pipes the commands into a pipe waiting that was started automatically at boot

pipe=/tmp/clockcommands

#RUN webcontrol/install.sh to copy this file to right place after changes

#TEST WITH:
#QUERY_STRING="clockmode&000000&when=1519847424544" (nope that doesnot work)
#sudo su www-data -s /bin/sh -c '/usr/lib/cgi-bin/light.cgi "Query= ticktest&000000&when=1519842067266"'

# make sure multipule copies of this script dont step on each other...


if [[ "$QUERY_STRING" == "leases"* ]]; then

        echo "<h2>Active digit leases</h2>"

        echo "<pre>"
        cat /var/lib/misc/dnsmasq.leases
        echo "</pre><br><hr><center>Hit back to return to menu</center>"
        

else

    echo "sending to pipe<br>"
    #pass command to the command reader

    echo "$QUERY_STRING" >$pipe

fi

echo 'Done<br>'

