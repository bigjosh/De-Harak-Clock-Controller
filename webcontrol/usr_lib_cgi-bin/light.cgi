#!/bin/bash
echo "Content-type: text/html"
echo ''
echo 'Query=' $QUERY_STRING
#./runleds.sh "$QUERY_STRING" 
echo "GOT:$QUERY_STRING" >> /tmp/light.log
echo 'CGI Color set<br>'
