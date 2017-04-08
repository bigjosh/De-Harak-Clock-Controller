#!/bin/sh
# ':' is the delimiter here, and there are three fields on each line in the file
# IFS set below is restricted to the context of `read`, it doesn't affect any other code
while IFS=' ' read -r field1 field2 field3 field4 field4 field5; do
  # process the fields
  # if the line has less than three fields, the missing fields will be set to to an empty string
  # if the line has more than three fields, `field3` will get the all the values, including the third field, including the delimiter(s)
 echo "$field2" "$field3"
done 
